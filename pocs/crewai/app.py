"""Independent HTTP API and OpenAI-compatible gateway for the CrewAI POC."""
from __future__ import annotations

import base64
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from integration.registry import load
from workflow import FactoryFlow, WorkflowRunner

REGISTRY = load()
RUN_ROOT = Path(os.getenv("RUN_ROOT", "/app/data/runs"))
POC_TARGETS = {**REGISTRY["agents"], **REGISTRY["teams"]}
app = FastAPI(title="Factory CrewAI POC", version="1.0.0")


def configure_tracing():
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    endpoint = os.getenv("LANGFUSE_OTEL_ENDPOINT", "").strip()
    if not (public_key and secret_key and endpoint):
        return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from openinference.instrumentation.crewai import CrewAIInstrumentor

    token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    provider = TracerProvider()
    provider.add_span_processor( BatchSpanProcessor(OTLPSpanExporter(
        endpoint=endpoint, headers={"Authorization": f"Basic {token}"})))
    trace.set_tracer_provider(provider)
    CrewAIInstrumentor().instrument(skip_dep_check=True)


configure_tracing()


def save_run(run: dict[str, Any]):
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    destination = RUN_ROOT / f"{run['run_id']}.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(destination)


def require_auth(authorization: str):
    api_key = os.getenv("CREWAI_API_KEY", "")
    if not api_key:
        raise HTTPException(503, "CREWAI_API_KEY is not configured")
    if not secrets.compare_digest(authorization, f"Bearer {api_key}"):
        raise HTTPException(401, "Invalid credentials")


async def request_body(request: Request) -> dict[str, Any]:
    if "application/json" in request.headers.get("content-type", ""):
        value = await request.json()
    else:
        value = dict(await request.form())
    if not isinstance(value, dict):
        raise HTTPException(400, "Request body must be an object")
    return value


def run_record(run_id: str, target: str, status: str, content: Any,
               runner: WorkflowRunner, started: float, **extra) -> dict[str, Any]:
    result = {
        "run_id": run_id,
        "status": status,
        "target": target,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": extra.pop("session_id", None),
        "step_results": runner.events,
        "metrics": {"duration": round(time.monotonic() - started, 3),
                    "total_tokens": runner.total_tokens},
        "definition_revision": REGISTRY["revision"],
        **extra,
    }
    save_run(result)
    return result


@app.get("/health")
async def health():
    return {"status": "ok", "platform": "crewai", "revision": REGISTRY["revision"]}


@app.get("/factory/revision")
async def revision():
    return {"revision": REGISTRY["revision"], "agents": len(REGISTRY["agents"]),
            "teams": len(REGISTRY["teams"]), "workflows": len(REGISTRY["workflows"])}


@app.get("/v1/models")
async def models():
    return {"object": "list", "data": [
        {"id": target, "object": "model", "created": 0, "owned_by": "crewai"}
        for target in POC_TARGETS
    ]}


@app.post("/agents/{agent_id}/runs")
async def run_agent(agent_id: str, request: Request,
                    authorization: str = Header(default=""),
                    x_user_id: str = Header(default=""),
                    x_conversation_id: str = Header(default="")):
    require_auth(authorization)
    if agent_id not in REGISTRY["agents"]:
        raise HTTPException(404, "Unknown agent")
    body = await request_body(request)
    message = body.get("message", "")
    if not isinstance(message, str) or not message:
        raise HTTPException(400, "message is required")
    runner = WorkflowRunner()
    started = time.monotonic()
    outcome = await run_in_threadpool(runner.run_agent_or_team, "agent", agent_id, message, {})
    status = "COMPLETED" if outcome["success"] else "FAILED"
    return run_record(runner.run_id, agent_id, status, outcome["output"], runner, started,
                      session_id=x_conversation_id or body.get("session_id"), user_id=x_user_id)


@app.post("/teams/{team_id}/runs")
async def run_team(team_id: str, request: Request,
                   authorization: str = Header(default=""),
                   x_user_id: str = Header(default=""),
                   x_conversation_id: str = Header(default="")):
    require_auth(authorization)
    if team_id not in REGISTRY["teams"]:
        raise HTTPException(404, "Unknown team")
    body = await request_body(request)
    message = body.get("message", "")
    if not isinstance(message, str) or not message:
        raise HTTPException(400, "message is required")
    runner = WorkflowRunner()
    started = time.monotonic()
    outcome = await run_in_threadpool(runner.run_agent_or_team, "team", team_id, message, {})
    status = "COMPLETED" if outcome["success"] else "FAILED"
    return run_record(runner.run_id, team_id, status, outcome["output"], runner, started,
                      session_id=x_conversation_id or body.get("session_id"), user_id=x_user_id)


@app.post("/workflows/{workflow_id}/runs")
async def run_workflow(workflow_id: str, request: Request,
                       authorization: str = Header(default=""),
                       x_user_id: str = Header(default=""),
                       x_conversation_id: str = Header(default="")):
    require_auth(authorization)
    if workflow_id not in REGISTRY["workflows"]:
        raise HTTPException(404, "Unknown workflow")
    body = await request_body(request)
    message = body.get("message", "")
    if not isinstance(message, str) or not message:
        raise HTTPException(400, "message is required")
    run_id = str(uuid.uuid4())
    started = time.monotonic()
    flow = FactoryFlow()
    try:
        output = await run_in_threadpool(flow.kickoff, inputs={
            "workflow_id": workflow_id,
            "message": message,
            "run_id": run_id,
            "user_id": x_user_id,
            "session_id": x_conversation_id,
        })
        if hasattr(output, "result"):
            output = output.result
        if not isinstance(output, dict):
            raise TypeError("CrewAI Flow returned an invalid result")
        content = output.get("content", {"result": "UNKNOWN", "released": False})
        status = "COMPLETED"
        runner = WorkflowRunner(run_id)
        runner.events = output.get("step_results", [])
        runner.total_tokens = output.get("metrics", {}).get("total_tokens", 0)
        return run_record(run_id, workflow_id, status, content, runner, started,
                          session_id=x_conversation_id, user_id=x_user_id,
                          flow_output=output)
    except Exception as error:
        runner = WorkflowRunner(run_id)
        failure = {"result": "UNKNOWN", "reason": f"{type(error).__name__}: {error}",
                   "approval": "UNKNOWN", "released": False}
        return run_record(run_id, workflow_id, "FAILED", failure, runner, started,
                          session_id=x_conversation_id, user_id=x_user_id)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str = Header(default=""),
                           x_user_id: str = Header(default=""),
                           x_conversation_id: str = Header(default="")):
    require_auth(authorization)
    body = await request.json()
    model = body.get("model")
    if model not in POC_TARGETS:
        raise HTTPException(400, "Unknown CrewAI agent or team")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages or messages[-1].get("role") != "user":
        raise HTTPException(400, "messages must end with a user message")
    if any(not isinstance(message.get("content"), str) for message in messages):
        raise HTTPException(400, "Only text messages are supported")
    transcript = "\n\n".join(f"{item['role']}: {item['content']}" for item in messages)
    runner = WorkflowRunner()
    started = time.monotonic()
    if model in REGISTRY["agents"]:
        outcome = await run_in_threadpool(runner.run_agent_or_team, "agent", model, transcript, {})
    else:
        outcome = await run_in_threadpool(runner.run_agent_or_team, "team", model, transcript, {})
    response = run_record(runner.run_id, model,
                          "COMPLETED" if outcome["success"] else "FAILED",
                          outcome["output"], runner, started,
                          session_id=x_conversation_id, user_id=x_user_id)
    content = response["content"]
    response_id = "chatcmpl-" + response["run_id"].replace("-", "")
    created = int(time.time())
    base = {"id": response_id, "created": created, "model": model}
    if body.get("stream"):
        async def events():
            for delta, finish in (({"role": "assistant", "content": content}, None), ({}, "stop")):
                chunk = {**base, "object": "chat.completion.chunk",
                         "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
                yield "data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(events(), media_type="text/event-stream")
    return {**base, "object": "chat.completion", "choices": [
        {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
    ]}
