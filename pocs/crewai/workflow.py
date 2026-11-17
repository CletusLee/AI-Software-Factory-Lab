"""CrewAI agents and CrewAI Flows for the shared factory definitions."""
from __future__ import annotations

import concurrent.futures
import difflib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from crewai.flow import Flow, start
from crewai.skills import discover_skills
from crewai.tools import tool
from pydantic import BaseModel, Field

from integration.registry import load

REGISTRY = load()
SCENARIO_ROOT = Path(os.getenv("SCENARIO_ROOT", "/app/scenarios"))
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/app/data/workspaces"))
RUN_ROOT = Path(os.getenv("RUN_ROOT", "/app/data/runs"))
MAX_PARALLEL_AGENTS = 4
MAX_AGENT_ITERATIONS = 1
TOOL_AGENT_MAX_ITERATIONS = 3
SKILL_AGENT_MAX_ITERATIONS = 3


def agent_max_iterations(spec: dict[str, Any], tools: list[Any]) -> int:
    """Reserve a final response iteration after native tools or skills run."""
    if tools:
        return TOOL_AGENT_MAX_ITERATIONS
    if spec.get("skills"):
        return SKILL_AGENT_MAX_ITERATIONS
    return MAX_AGENT_ITERATIONS


def make_model() -> LLM:
    model_id = os.getenv("MODEL_ID", "")
    if not model_id:
        raise ValueError("MODEL_ID is required")
    return LLM(
        model=f"openai/{model_id}",
        custom_openai=True,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        api_key=os.getenv("OPENAI_API_KEY") or None,
        temperature=0,
        timeout=90,
        max_retries=0,
    )


def load_skills():
    skills_root = REGISTRY["root"] / "skills"
    return {skill.name: skill for skill in discover_skills(skills_root)}


@tool("check_ticket_readiness")
def check_ticket_readiness(work_item_id: str, scenario: str = "stale") -> str:
    """Read the PAY-482 evidence fixture for stale, passed, or timeout scenarios."""
    work_id = work_item_id.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", work_id):
        return json.dumps({"recommendation": "UNKNOWN", "reason": "Invalid work item ID."})
    scenario_dir = (SCENARIO_ROOT / work_id.lower()).resolve()
    if SCENARIO_ROOT.resolve() not in scenario_dir.parents:
        return json.dumps({"recommendation": "UNKNOWN", "reason": "Invalid work item path."})
    try:
        item = json.loads((scenario_dir / "work-item.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return json.dumps({"recommendation": "UNKNOWN", "reason": "Fixture is unavailable."})
    if item.get("id") != work_id:
        return json.dumps({"recommendation": "UNKNOWN", "reason": "Work item ID does not match."})
    fixture = item.get("evidence", {}).get("scenarios", {}).get(scenario)
    if not fixture:
        return json.dumps({"recommendation": "UNKNOWN", "reason": "Unknown evidence scenario."})
    return json.dumps(
        {"work_item_id": work_id, "scenario": scenario, **fixture,
         "source": item.get("evidence", {}).get("source", "repository fixture")},
        ensure_ascii=False,
    )


class WorkflowState(BaseModel):
    workflow_id: str = ""
    message: str = ""
    run_id: str = ""
    user_id: str = ""
    session_id: str = ""
    result: dict[str, Any] = Field(default_factory=dict)


class FactoryFlow(Flow[WorkflowState]):
    """Execute the definition's branches and agent calls inside a CrewAI Flow."""

    @start()
    def run_definition(self) -> dict[str, Any]:
        definition = REGISTRY["workflows"].get(self.state.workflow_id)
        if definition is None:
            raise ValueError(f"Unknown workflow: {self.state.workflow_id}")
        runner = WorkflowRunner(self.state.run_id)
        request = runner.parse_request(self.state.message)
        output = runner.run_steps(definition["steps"], request)
        content = output.get("output") if output else None
        if definition["id"] == "continuous-improvement" and content:
            content = {"result": "COMPLETED", "summary": content, "released": False}
        if not isinstance(content, dict):
            content = {"work_id": request.get("work_id", "UNKNOWN"),
                       "result": "UNKNOWN", "reason": "Workflow produced no result.",
                       "approval": "UNKNOWN", "released": False}
        return {
            "workflow_id": definition["id"],
            "content": content,
            "step_results": runner.events,
            "metrics": {"duration": round(time.monotonic() - runner.started, 3),
                        "total_tokens": runner.total_tokens},
        }


class WorkflowRunner:
    def __init__(self, run_id: str = ""):
        self.run_id = run_id or uuid.uuid4().hex
        self.started = time.monotonic()
        self.events: list[dict[str, Any]] = []
        self.total_tokens = 0
        self._lock = threading.Lock()
        self._model: LLM | None = None
        self._skills: dict[str, Any] | None = None

    @staticmethod
    def parse_request(message: str) -> dict[str, Any]:
        try:
            parsed = json.loads(message)
        except (TypeError, ValueError):
            return {"message": message}
        return parsed if isinstance(parsed, dict) else {"message": message}

    def _agent(self, agent_id: str) -> Agent:
        spec = REGISTRY["agents"].get(agent_id)
        if spec is None:
            raise ValueError(f"Unknown agent: {agent_id}")
        if self._model is None:
            self._model = make_model()
        if self._skills is None:
            self._skills = load_skills()
        missing = set(spec.get("skills", [])) - self._skills.keys()
        if missing:
            raise ValueError(f"{agent_id} references missing skills: {sorted(missing)}")
        tools = [check_ticket_readiness] if agent_id == "sdlc-ticket-agent" else []
        return Agent(
            role=spec["name"],
            goal=spec.get("summary", spec["name"]),
            backstory=spec["prompt"],
            llm=self._model,
            tools=tools,
            skills=[self._skills[name] for name in spec.get("skills", [])],
            allow_delegation=False,
            max_iter=agent_max_iterations(spec, tools),
            max_retry_limit=0,
            verbose=False,
        )

    def run_agent_or_team(self, kind: str, target: str, message: str,
                          previous: dict[str, Any]) -> dict[str, Any]:
        task_started = time.monotonic()
        try:
            inputs = {
                "request": message,
                "previous_results": json.dumps(previous, ensure_ascii=False, default=str),
            }
            if kind == "agent":
                agents = [self._agent(target)]
                team_name = None
            else:
                team = REGISTRY["teams"].get(target)
                if team is None:
                    raise ValueError(f"Unknown team: {target}")
                agents = [self._agent(agent_id) for agent_id in team["members"]]
                team_name = team["name"]
            tasks = []
            for index, agent in enumerate(agents):
                heading = f"Team {team_name}: member {index + 1} of {len(agents)}" if team_name else agent.role
                tasks.append(Task(
                    description=(
                        f"{heading}. Complete the factory request below using the stated evidence. "
                        "Use UNKNOWN when information is missing.\n\n"
                        "Request:\n{request}\n\n"
                        "Prior workflow outputs (JSON):\n{previous_results}"
                    ),
                    expected_output="A concise result with conclusions, evidence, and remaining unknowns.",
                    agent=agent,
                ))
            crew = Crew(agents=agents, tasks=tasks, process=Process.sequential,
                        verbose=False, tracing=False)
            result = crew.kickoff(inputs=inputs)
            usage = getattr(result, "token_usage", None)
            tokens = int(getattr(usage, "total_tokens", 0) or 0)
            with self._lock:
                self.total_tokens += tokens
            return {"output": str(getattr(result, "raw", result)), "success": True,
                    "tokens": tokens,
                    "duration": round(time.monotonic() - task_started, 3)}
        except Exception as error:
            return {"output": "UNKNOWN", "success": False, "tokens": 0,
                    "duration": round(time.monotonic() - task_started, 3),
                    "error": f"{type(error).__name__}: {error}"}

    def _record(self, name: str, kind: str, outcome: dict[str, Any]):
        with self._lock:
            self.events.append({
                "step_name": name,
                "type": kind.upper(),
                "success": outcome.get("success", True),
                "output": outcome.get("output"),
                "duration_seconds": outcome.get("duration", 0),
                "tokens": outcome.get("tokens", 0),
                "error": outcome.get("error"),
            })

    def _run_agent_step(self, step: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        outcome = self.run_agent_or_team(step["type"], step["ref"],
                                         json.dumps(context["request"], ensure_ascii=False),
                                         context["outputs"])
        self._record(step["name"], step["type"], outcome)
        return outcome

    def run_steps(self, steps: list[dict[str, Any]], request: dict[str, Any],
                  outputs: dict[str, Any] | None = None) -> dict[str, Any]:
        outputs = outputs if outputs is not None else {}
        last: dict[str, Any] = {}
        context = {"request": request, "outputs": outputs}
        for step in steps:
            kind = step["type"]
            if kind == "condition":
                if step["ref"] == "is_ready":
                    evidence = outputs.get("Evidence Gate", {}).get("output", {})
                    selected = step["steps"] if isinstance(evidence, dict) and evidence.get("recommendation") == "READY" else step["else_steps"]
                elif step["ref"] == "candidate_passed":
                    verification = outputs.get("Candidate Verification", {}).get("output", {})
                    selected = step["steps"] if isinstance(verification, dict) and verification.get("test_status") == "PASS" else step["else_steps"]
                else:
                    self._record(step["name"], kind, {"success": False, "output": "UNKNOWN",
                                                       "error": f"Unknown condition: {step['ref']}"})
                    last = {"success": False, "output": {"result": "UNKNOWN", "released": False}}
                    continue
                self._record(step["name"], kind, {"success": True, "output": "TRUE" if selected is step["steps"] else "FALSE"})
                last = self.run_steps(selected, request, outputs) or last
                continue
            if kind == "parallel":
                if not step["steps"]:
                    continue
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(MAX_PARALLEL_AGENTS, len(step["steps"]))
                ) as pool:
                    futures = {pool.submit(self._run_agent_step, child, context): child
                               for child in step["steps"]}
                    results = {}
                    for future, child in futures.items():
                        results[child["name"]] = future.result()
                outputs.update(results)
                last = next(iter(results.values()), last)
                continue
            if kind in ("agent", "team"):
                last = self._run_agent_step(step, context)
                outputs[step["name"]] = last
                continue
            if kind == "executor":
                outcome = self._run_executor(step["ref"], request, outputs)
                self._record(step["name"], kind, outcome)
                outputs[step["name"]] = outcome
                last = outcome
                if outcome.get("stop"):
                    break
                continue
            outcome = {"success": False, "output": "UNKNOWN", "error": f"Unknown step type: {kind}"}
            self._record(step["name"], kind, outcome)
            last = outcome
        return last

    def _run_executor(self, name: str, request: dict[str, Any],
                      outputs: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "evidence_gate":
                work_id = request.get("work_id", request.get("work_item_id", "UNKNOWN"))
                try:
                    _, item = load_work_item(work_id)
                    fixture = item.get("evidence", {}).get("scenarios", {}).get(request.get("scenario"), {})
                    source = item.get("evidence", {}).get("source", "repository fixture")
                except (OSError, ValueError, TypeError):
                    fixture, source = {}, "Evidence fixture unavailable."
                result = {"work_id": work_id,
                          "recommendation": fixture.get("recommendation", "UNKNOWN"),
                          "reason": fixture.get("reason", "Required evidence is missing."),
                          "candidate_commit": fixture.get("candidate_commit", "UNKNOWN"),
                          "tested_commit": fixture.get("tested_commit", "UNKNOWN"),
                          "approval": "UNKNOWN: waiting for human review",
                          "source": fixture.get("source", source)}
            elif name == "apply_candidate_change":
                result = apply_candidate_change(request)
            elif name == "verify_candidate":
                result = verify_candidate(outputs.get("Apply Candidate Change", {}).get("output", {}))
            elif name == "blocked_result":
                evidence = outputs.get("Evidence Gate", {}).get("output", {})
                test = outputs.get("Candidate Verification", {}).get("output", {})
                test_status = test.get("test_status")
                if not test_status:
                    state = evidence.get("recommendation", "UNKNOWN")
                elif test_status == "PASS":
                    state = "UNKNOWN"
                else:
                    state = "READY_FOR_REWORK"
                result = {"work_id": evidence.get("work_id", request.get("work_id", "UNKNOWN")),
                          "result": state,
                          "reason": test.get("test_output") if test_status and test_status != "PASS" else evidence.get("reason", "Evidence is missing."),
                          "candidate_test_status": test_status or "NOT RUN",
                          "candidate_evidence_path": test.get("evidence_path"),
                          "approval": "UNKNOWN", "released": False}
            elif name == "pending_approval":
                incomplete = [event["step_name"] for event in self.events if not event["success"]]
                if incomplete:
                    result = {"work_id": request.get("work_id", request.get("work_item_id", "UNKNOWN")),
                              "result": "UNKNOWN", "reason": "Required step failed: " + ", ".join(incomplete),
                              "approval": "UNKNOWN", "released": False}
                else:
                    result = {"work_id": request.get("work_id", request.get("work_item_id", "UNKNOWN")),
                              "result": "READY_FOR_HUMAN_REVIEW",
                              "approval": "UNKNOWN: awaiting QA or release owner",
                              "released": False,
                              "note": "The POC ends at the human review gate."}
            elif name in ("require_observability", "require_governance"):
                team_step = "Observability" if name == "require_observability" else "Governance"
                previous = outputs.get(team_step, {})
                if not previous.get("success"):
                    return {"success": True, "stop": True,
                            "output": "UNKNOWN: required team execution failed; flow stopped."}
                result = previous.get("output")
            else:
                raise ValueError(f"Unknown executor: {name}")
            return {"success": True, "output": result, "duration": 0, "tokens": 0}
        except Exception as error:
            return {"success": False, "output": {"result": "UNKNOWN", "released": False},
                    "error": f"{type(error).__name__}: {error}", "duration": 0, "tokens": 0}


def safe_relative(base: Path, value: str) -> Path:
    path_value = Path(value)
    if path_value.is_absolute():
        raise ValueError(f"Expected a relative path: {value}")
    path = (base / path_value).resolve()
    root = base.resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"Path escapes its allowed directory: {value}")
    return path


def load_work_item(work_id: str) -> tuple[Path, dict[str, Any]]:
    if not isinstance(work_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", work_id):
        raise ValueError("A valid work_id is required")
    scenario_dir = safe_relative(SCENARIO_ROOT, work_id.lower())
    item = json.loads(safe_relative(scenario_dir, "work-item.json").read_text(encoding="utf-8"))
    if item.get("id") != work_id:
        raise ValueError("Work item ID does not match its scenario directory")
    return scenario_dir, item


def apply_candidate_change(request: dict[str, Any]) -> dict[str, Any]:
    work_id = request.get("work_id", request.get("work_item_id", ""))
    scenario_dir, item = load_work_item(work_id)
    candidate = item["candidate"]
    baseline = safe_relative(scenario_dir, candidate["baseline_dir"])
    files = candidate["files"]
    if not files or any(not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts for name in files):
        raise ValueError("Work item must declare safe relative source files")
    workspace = WORKSPACE_ROOT / work_id.lower() / uuid.uuid4().hex
    workspace.mkdir(parents=True, exist_ok=False)
    for name in files:
        source = safe_relative(baseline, name)
        if not source.is_file():
            source = safe_relative(scenario_dir, name)
        if not source.is_file():
            raise ValueError(f"Work item source file is missing: {name}")
        destination = safe_relative(workspace, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    command = candidate["test_command"]
    if not isinstance(command, list) or not command or command[0] not in ("python", "python3"):
        raise ValueError("Only a Python test command is allowed in this POC")
    before = subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=60, check=False)
    red_output = (before.stdout + before.stderr)[-6000:]
    failure_marker = candidate.get("expected_baseline_failure")
    if not isinstance(failure_marker, str) or failure_marker not in red_output or before.returncode == 0:
        raise ValueError("Baseline did not reproduce the expected regression")
    diffs, changed = [], []
    for change in candidate["changes"]:
        name = change["path"]
        if name not in files:
            raise ValueError(f"Patch target is outside the declared file scope: {name}")
        target = safe_relative(workspace, name)
        original = target.read_text(encoding="utf-8")
        if original.count(change["old"]) != 1:
            raise ValueError(f"Patch context must match exactly once in {name}")
        updated = original.replace(change["old"], change["new"], 1)
        target.write_text(updated, encoding="utf-8")
        changed.append(name)
        diffs.extend(difflib.unified_diff(original.splitlines(keepends=True), updated.splitlines(keepends=True),
                                          fromfile="before/" + name, tofile="after/" + name))
    evidence = {"work_id": work_id, "workspace_id": workspace.name, "workspace_path": str(workspace),
                "changed_files": changed, "baseline_test_status": "EXPECTED_FAIL",
                "baseline_test_output": red_output, "patch_diff": "".join(diffs),
                "acceptance_criteria": item.get("acceptance_criteria", []), "test_command": command,
                "note": "Candidate changes are isolated, uncommitted, and not deployed."}
    (workspace / "candidate-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return evidence


def verify_candidate(applied: dict[str, Any]) -> dict[str, Any]:
    workspace = Path(applied.get("workspace_path", ""))
    if not applied.get("workspace_id") or not workspace.is_dir():
        return {"test_status": "UNKNOWN", "reason": "Candidate workspace is missing."}
    command = applied.get("test_command")
    if not isinstance(command, list) or not command or command[0] not in ("python", "python3"):
        return {"test_status": "UNKNOWN", "reason": "Invalid acceptance test command."}
    try:
        result = subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=60, check=False)
        status = "PASS" if result.returncode == 0 else "FAIL"
        output = (result.stdout + result.stderr)[-6000:]
        exit_code = result.returncode
    except (OSError, subprocess.TimeoutExpired) as error:
        status, output, exit_code = "UNKNOWN", type(error).__name__, None
    evidence = {"work_id": applied.get("work_id"), "workspace_id": applied.get("workspace_id"),
                "changed_files": applied.get("changed_files", []), "test_command": command,
                "test_status": status, "exit_code": exit_code, "test_output": output,
                "patch_diff": applied.get("patch_diff", ""),
                "baseline_test_status": applied.get("baseline_test_status"),
                "baseline_test_output": applied.get("baseline_test_output", ""),
                "evidence_path": str(workspace / "candidate-evidence.json")}
    (workspace / "candidate-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return evidence
