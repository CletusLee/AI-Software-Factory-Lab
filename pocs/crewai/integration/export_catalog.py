"""Export shared factory definitions into a standalone Backstage catalog."""
import json
from pathlib import Path

from integration.registry import load


def export(registry=None, destination=None):
    registry = registry or load()
    destination = Path(destination or "/app/integration/catalog/entities.yaml")
    data_root = Path(__file__).resolve().parents[1] / "data"
    entities = []

    def entity_ref(key):
        return f"component:default/{key}"

    def add(kind, key, obj, description, dependencies=(), annotations=None):
        spec = {"type": kind, "lifecycle": "experimental", "owner": "guests"}
        if dependencies:
            spec["dependsOn"] = [entity_ref(item) for item in sorted(set(dependencies))]
        entity_annotations = {"factory.local/id": str(obj["id"]),
                              "factory.local/revision": registry["revision"]}
        if annotations:
            entity_annotations.update({name: str(value) for name, value in annotations.items()})
        entities.append({
            "apiVersion": "backstage.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": key, "title": obj.get("name", key),
                         "description": description,
                         "annotations": entity_annotations},
            "spec": spec,
        })

    for key, agent in registry["agents"].items():
        add("agent", key, agent, agent.get("summary", agent["prompt"][:180]),
            dependencies=agent.get("skills", []))
    for key, team in registry["teams"].items():
        add("agent-team", key, team, team["prompt"][:180],
            dependencies=team["members"])

    def referenced_components(steps):
        dependencies = set()
        for step in steps:
            if step.get("type") in ("agent", "team"):
                dependencies.add(step["ref"])
            dependencies.update(referenced_components(step.get("steps", [])))
            dependencies.update(referenced_components(step.get("else_steps", [])))
        return dependencies

    for key, flow in registry["workflows"].items():
        add("workflow", key, flow, flow["description"],
            dependencies=referenced_components(flow["steps"]))
    for key, path in registry["skills"].items():
        add("agent-skill", key, {"id": key, "name": key},
            path.read_text(encoding="utf-8")[:180])

    benchmark_path = data_root / "benchmark-results.json"
    native_path = data_root / "native-results.json"
    if benchmark_path.is_file():
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        native = json.loads(native_path.read_text(encoding="utf-8")) if native_path.is_file() else {}
        native_by_scenario = {item["scenario"]: item for item in native.get("cases", [])}
        for case in benchmark.get("cases", []):
            scenario = case["id"]
            expected = str(case.get("expected", "UNKNOWN"))
            actual = str(case.get("actual", "UNKNOWN"))
            valid = actual == expected
            record = native_by_scenario.get(scenario, {}).get("run", {})
            content = record.get("content") or {}
            failures = [
                f"{item['step_name']}: {item['error']}"
                for item in record.get("step_results", [])
                if not item.get("success") or item.get("error")
            ]
            candidate = next(
                (item.get("output", {}) for item in record.get("step_results", [])
                 if item.get("step_name") == "Candidate Verification"), {})
            description = (
                f"PAY-482 {scenario} scenario: expected {expected}; actual {actual}; "
                f"{'PASS' if valid else 'INCOMPLETE'}. "
                f"released={str(content.get('released', False)).lower()}."
            )
            if candidate:
                description += (
                    f" Candidate baseline={candidate.get('baseline_test_status', 'UNKNOWN')}; "
                    f"acceptance={candidate.get('test_status', 'UNKNOWN')}."
                )
            if failures:
                description += " " + "; ".join(failures)
            annotations = {
                "factory.local/expected": expected,
                "factory.local/actual": actual,
                "factory.local/status": "PASS" if valid else "INCOMPLETE",
                "factory.local/evidence-ref": case.get("evidence_ref", "UNKNOWN"),
                "factory.local/released": str(content.get("released", False)).lower(),
            }
            if candidate:
                annotations["factory.local/candidate-test"] = str(candidate.get("test_status", "UNKNOWN"))
            add("benchmark-case", f"pay-482-{scenario}",
                {"id": f"PAY-482-{scenario}", "name": f"PAY-482 / {scenario}"},
                description, dependencies=["software-delivery"], annotations=annotations)

    improvement_path = data_root / "continuous-improvement-run.json"
    if improvement_path.is_file():
        run = json.loads(improvement_path.read_text(encoding="utf-8"))
        content = run.get("content") or {}
        failed_steps = [
            f"{item['step_name']}: {item['error']}"
            for item in run.get("step_results", [])
            if not item.get("success") or item.get("error")
        ]
        description = (
            "Continuous Improvement run: "
            + str(content.get("summary", content.get("result", "UNKNOWN")))
            + ". " + "; ".join(failed_steps)
        ).strip()
        add("workflow-run", "continuous-improvement-run",
            {"id": run.get("run_id", "continuous-improvement-run"),
             "name": "Continuous Improvement / latest run"},
            description, dependencies=["continuous-improvement"], annotations={
                "factory.local/run-status": run.get("status", "UNKNOWN"),
                "factory.local/result": content.get("result", "UNKNOWN"),
                "factory.local/released": str(content.get("released", False)).lower(),
                "factory.local/run-id": run.get("run_id", "UNKNOWN"),
            })

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n---\n".join(json.dumps(entity, ensure_ascii=False, indent=2)
                                                 for entity in entities) + "\n", encoding="utf-8")
    return len(entities)


if __name__ == "__main__":
    count = export()
    print(f"Exported CrewAI catalog: {count} entities, revision {load()['revision']}")
