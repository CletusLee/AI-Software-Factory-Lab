"""Delivery must never mark an incomplete Agent review ready for humans."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agno.workflow.types import StepInput, StepOutput
import native_workflows
from native_workflows import evidence_gate, pending_approval


class ApprovalGateTests(unittest.TestCase):
    def test_failed_reviewer_is_unknown(self):
        names = ('Evidence Gate', 'Knowledge', 'Plan', 'Orchestrate', 'Design', 'Code Proposal',
                 'Infrastructure Proposal', 'Integration Proposal', 'Apply Candidate Change',
                 'Candidate Verification', 'Testing', 'Security', 'Reliability', 'Review', 'Risk Summary')
        outputs = {name: StepOutput(step_name=name, success=name != 'Review') for name in names}
        result = pending_approval(StepInput(previous_step_outputs=outputs))
        self.assertEqual(result.content['result'], 'UNKNOWN')
        self.assertIn('Review', result.content['reason'])
        self.assertFalse(result.content['released'])

    def test_all_successful_steps_require_human_review(self):
        names = ('Evidence Gate', 'Knowledge', 'Plan', 'Orchestrate', 'Design', 'Code Proposal',
                 'Infrastructure Proposal', 'Integration Proposal', 'Apply Candidate Change',
                 'Candidate Verification', 'Testing', 'Security', 'Reliability', 'Review', 'Risk Summary')
        outputs = {name: StepOutput(step_name=name, success=True) for name in names}
        result = pending_approval(StepInput(previous_step_outputs=outputs))
        self.assertEqual(result.content['result'], 'READY_FOR_HUMAN_REVIEW')
        self.assertFalse(result.content['released'])

    def test_missing_step_is_unknown(self):
        self.assertEqual(pending_approval(StepInput()).content['result'], 'UNKNOWN')

    def test_evidence_gate_uses_work_item_scenario_fixture(self):
        ready = json.loads(evidence_gate(
            StepInput(input={'work_id': 'PAY-482', 'scenario': 'ready'})).content)
        missing = json.loads(evidence_gate(
            StepInput(input={'work_id': 'PAY-482', 'scenario': 'unlisted'})).content)
        self.assertEqual(ready['recommendation'], 'READY')
        self.assertEqual(missing['recommendation'], 'UNKNOWN')

    def test_candidate_change_reproduces_red_then_green_in_isolated_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(native_workflows, 'WORKSPACE_ROOT', Path(temporary)):
                request = StepInput(input={'work_id': 'PAY-482', 'scenario': 'ready'})
                applied = native_workflows.apply_candidate_change(request)
                apply_evidence = json.loads(applied.content)
                output = StepOutput(step_name='Apply Candidate Change', content=applied.content, success=True)
                verified = native_workflows.verify_candidate(
                    StepInput(previous_step_outputs={'Apply Candidate Change': output}))
                evidence = json.loads(verified.content)
        self.assertEqual(apply_evidence['baseline_test_status'], 'EXPECTED_FAIL')
        self.assertIn(apply_evidence['baseline_failure_marker'], apply_evidence['baseline_test_output'])
        self.assertEqual(apply_evidence['changed_files'], ['payment_demo.py'])
        self.assertIn('raise ValueError', apply_evidence['patch_diff'])
        self.assertEqual(evidence['test_status'], 'PASS')
        self.assertEqual(evidence['baseline_test_status'], 'EXPECTED_FAIL')
        self.assertIn(evidence['baseline_failure_marker'], evidence['baseline_test_output'])


if __name__ == '__main__':
    unittest.main()
