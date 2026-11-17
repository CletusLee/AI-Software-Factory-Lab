"""Run the shared PAY-482 benchmark against the CrewAI POC API."""
import argparse
import json
import os
import time
from importlib.metadata import version
from pathlib import Path

import jsonschema
import requests

API_URL = os.getenv("CREWAI_URL", "http://localhost:7790")
HEADERS = {"Authorization": "Bearer " + os.environ["CREWAI_API_KEY"]}
ROOT = Path(os.getenv("FACTORY_ROOT", "/app" if Path(__file__).resolve().parent == Path("/app")
                                     else Path(__file__).resolve().parents[2]))
OUTPUT = Path(os.getenv("CREWAI_OUTPUT", Path(__file__).parent / "data"))
benchmark = json.loads((ROOT / "benchmark" / "pay-482-cases.json").read_text(encoding="utf-8"))
schema = json.loads((ROOT / "benchmark" / "result.schema.json").read_text(encoding="utf-8"))

parser = argparse.ArgumentParser(description=__doc__)
mode = parser.add_mutually_exclusive_group()
mode.add_argument("--delivery-only", action="store_true")
mode.add_argument("--improvement-only", action="store_true")
mode.add_argument("--scenario", choices=[case["id"] for case in benchmark["cases"]],
                   help="Rerun one delivery case and merge its result into the saved benchmark")
args = parser.parse_args()
records = []
revision = requests.get(API_URL + "/factory/revision", timeout=10).json()
benchmark_path = OUTPUT / "benchmark-results.json"
native_results_path = OUTPUT / "native-results.json"
if args.improvement_only or args.scenario:
    if not benchmark_path.is_file():
        raise SystemExit("Run the delivery benchmark before a partial rerun")
    comparison = json.loads(benchmark_path.read_text(encoding="utf-8"))
    if comparison.get("definition_revision") != revision["revision"]:
        raise SystemExit("The saved delivery benchmark uses a different definition revision")
    if args.scenario:
        if not native_results_path.is_file():
            raise SystemExit("The saved native run results are required for a partial rerun")
        records = json.loads(native_results_path.read_text(encoding="utf-8")).get("cases", [])
        comparison["model_parameters"] = {
            "temperature": 0, "timeout_seconds": 90, "max_agent_iterations": 1,
            "tool_agent_max_iterations": 3, "skill_agent_max_iterations": 3,
        }
else:
    comparison = {"poc": "crewai", "platform_version": version("crewai"),
                  "definition_revision": revision["revision"],
                  "scenario_version": str(benchmark["version"]),
                  "model": os.getenv("MODEL_ID", "UNKNOWN"),
                  "model_parameters": {"temperature": 0, "timeout_seconds": 90,
                                       "max_agent_iterations": 1,
                                       "tool_agent_max_iterations": 3,
                                       "skill_agent_max_iterations": 3},
                  "cases": []}
if not args.improvement_only:
    cases_to_run = [case for case in benchmark["cases"]
                    if not args.scenario or case["id"] == args.scenario]
    for case in cases_to_run:
        started = time.monotonic()
        response = requests.post(API_URL + "/workflows/software-delivery/runs", headers=HEADERS,
                                 data={"message": case["message"]}, timeout=900)
        response.raise_for_status()
        run = response.json()
        content = run.get("content") or {}
        valid = (run.get("status") == "COMPLETED" and isinstance(content, dict)
                 and content.get("result") == case["expected"]
                 and content.get("released") is False)
        new_record = {"scenario": case["id"], "expected": case["expected"],
                      "valid": valid, "run": run}
        records = [item for item in records if item.get("scenario") != case["id"]]
        records.append(new_record)
        records.sort(key=lambda item: next(
            (i for i, benchmark_case in enumerate(benchmark["cases"])
             if benchmark_case["id"] == item.get("scenario")), len(benchmark["cases"])))
        result_case = {"id": case["id"], "expected": case["expected"],
            "actual": content.get("result", "UNKNOWN"), "execution_status": run.get("status", "UNKNOWN"),
            "duration_seconds": round(time.monotonic() - started, 3),
            "tokens": (run.get("metrics") or {}).get("total_tokens"), "evidence_ref": run.get("run_id")}
        comparison["cases"] = [item for item in comparison["cases"] if item.get("id") != case["id"]]
        comparison["cases"].append(result_case)
        comparison["cases"].sort(key=lambda item: next(
            (i for i, benchmark_case in enumerate(benchmark["cases"])
             if benchmark_case["id"] == item.get("id")), len(benchmark["cases"])))
        OUTPUT.mkdir(parents=True, exist_ok=True)
        native_results_path.write_text(json.dumps({"cases": records}, ensure_ascii=False, indent=2), encoding="utf-8")
        benchmark_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
        print(case["id"], "PASS" if valid else "FAIL", run.get("run_id"), flush=True)

improvement_ok = True
if not args.delivery_only and not args.scenario:
    response = requests.post(API_URL + "/workflows/continuous-improvement/runs", headers=HEADERS,
        data={"message": "依最新工作項目執行結果與觀測證據，提出可驗證的改善草案；不得宣稱已部署。"}, timeout=900)
    response.raise_for_status()
    improvement = response.json()
    (OUTPUT / "continuous-improvement-run.json").write_text(json.dumps(improvement, ensure_ascii=False, indent=2), encoding="utf-8")
    improvement_ok = improvement.get("status") == "COMPLETED" and all(
        item.get("success") for item in improvement.get("step_results", []))
    print("continuous-improvement", "PASS" if improvement_ok else "INCOMPLETE", improvement.get("run_id"), flush=True)

jsonschema.validate(comparison, schema)
delivery_ok = all(item["valid"] for item in records) if records else args.improvement_only
if not delivery_ok or not improvement_ok:
    raise SystemExit("CrewAI POC benchmark did not meet all expected results")
