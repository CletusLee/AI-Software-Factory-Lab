import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import workflow
from app import app, REGISTRY
from fastapi.testclient import TestClient
from integration.registry import load
from workflow import (WorkflowRunner, agent_max_iterations, apply_candidate_change,
                      verify_candidate)


class SharedDefinitionsTests(unittest.TestCase):
    def test_shared_factory_definitions_are_available(self):
        registry = load()

        self.assertEqual(len(registry["agents"]), 26)
        self.assertEqual(len(registry["teams"]), 3)
        self.assertEqual(len(registry["workflows"]), 2)
        self.assertEqual(len(registry["skills"]), 14)


class WorkflowGateTests(unittest.TestCase):
    def test_agents_with_skills_get_a_final_response_iteration(self):
        self.assertEqual(agent_max_iterations({"skills": ["audit"]}, []), 3)
        self.assertEqual(agent_max_iterations({"skills": []}, [object()]), 3)
        self.assertEqual(agent_max_iterations({"skills": []}, []), 1)

    def test_non_ready_benchmark_cases_stop_before_agent_calls(self):
        registry = load()
        workflow_definition = registry["workflows"]["software-delivery"]
        expected = {"stale": "NOT READY", "timeout": "UNKNOWN", "fail": "NOT READY"}

        for scenario, result in expected.items():
            with self.subTest(scenario=scenario):
                runner = WorkflowRunner()
                request = {"work_id": "PAY-482", "scenario": scenario}
                outcome = runner.run_steps(workflow_definition["steps"], request)

                self.assertEqual(outcome["output"]["result"], result)
                self.assertFalse(outcome["output"]["released"])
                self.assertEqual([event["step_name"] for event in runner.events],
                                 ["Evidence Gate", "Readiness", "Needs Evidence or Rework"])


class ApiSurfaceTests(unittest.TestCase):
    def test_health_registry_and_model_list(self):
        with TestClient(app) as client:
            health = client.get("/health")
            revision = client.get("/factory/revision")
            models = client.get("/v1/models")

        self.assertEqual(health.json()["platform"], "crewai")
        self.assertEqual(revision.json()["agents"], 26)
        self.assertEqual(revision.json()["teams"], 3)
        self.assertEqual(revision.json()["workflows"], 2)
        self.assertEqual({item["id"] for item in models.json()["data"]},
                         set(REGISTRY["agents"]) | set(REGISTRY["teams"]))

    def test_run_endpoint_requires_api_key(self):
        with TestClient(app) as client:
            response = client.post("/agents/factory-01/runs", json={"message": "test"})

        self.assertEqual(response.status_code, 401)

    def test_failed_required_step_blocks_human_review(self):
        runner = WorkflowRunner()
        runner.events.append({"step_name": "Review", "success": False})
        outcome = runner._run_executor("pending_approval", {"work_id": "PAY-482"}, {})

        self.assertEqual(outcome["output"]["result"], "UNKNOWN")
        self.assertFalse(outcome["output"]["released"])


class CandidateWorkspaceTests(unittest.TestCase):
    def test_candidate_fails_on_baseline_then_passes_after_patch(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(workflow, "WORKSPACE_ROOT", Path(temporary)):
                applied = apply_candidate_change({"work_id": "PAY-482"})
                verified = verify_candidate(applied)

        self.assertEqual(applied["baseline_test_status"], "EXPECTED_FAIL")
        self.assertIn("test_same_event_with_conflicting_amount_is_rejected",
                      applied["baseline_test_output"])
        self.assertEqual(verified["test_status"], "PASS")
        self.assertIn("payment_demo.py", verified["changed_files"])


if __name__ == "__main__":
    unittest.main()
