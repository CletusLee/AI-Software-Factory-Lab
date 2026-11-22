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
    def successful_outputs(self, review, failed=()):
        names = ('Evidence Gate', 'Knowledge', 'Plan', 'Orchestrate', 'Design', 'Code Proposal',
                 'Infrastructure Proposal', 'Integration Proposal', 'Apply Candidate Change',
                 'Candidate Verification', 'Testing', 'Security', 'Reliability', 'Review', 'Risk Summary')
        return {
            name: StepOutput(step_name=name,
                             content=json.dumps(review) if name == 'Review' else '{}',
                             success=name not in failed)
            for name in names
        }

    def test_failed_reviewer_is_unknown(self):
        outputs = self.successful_outputs({'decision': 'CLEAR', 'blockers': []}, failed=('Review',))
        result = pending_approval(StepInput(previous_step_outputs=outputs))
        self.assertEqual(result.content['result'], 'UNKNOWN')
        self.assertIn('Review', result.content['reason'])
        self.assertFalse(result.content['released'])

    def test_all_successful_steps_require_human_review(self):
        outputs = self.successful_outputs({'decision': 'CLEAR', 'blockers': []})
        result = pending_approval(StepInput(previous_step_outputs=outputs))
        self.assertEqual(result.content['result'], 'READY_FOR_HUMAN_REVIEW')
        self.assertFalse(result.content['released'])

    def test_reviewer_blockers_require_rework(self):
        outputs = self.successful_outputs({
            'decision': 'REQUEST_CHANGES',
            'blockers': ['The original ledger entry is not asserted.'],
        })
        result = pending_approval(StepInput(
            input={'work_id': 'PAY-482'}, previous_step_outputs=outputs))
        self.assertEqual(result.content['result'], 'READY_FOR_REWORK')
        self.assertIn('original ledger entry', result.content['reason'][0])
        self.assertFalse(result.content['released'])

    def test_unreadable_review_is_unknown(self):
        outputs = self.successful_outputs({'decision': 'UNCLEAR', 'blockers': []})
        result = pending_approval(StepInput(previous_step_outputs=outputs))
        self.assertEqual(result.content['result'], 'UNKNOWN')

    def test_baseline_gate_keeps_the_previous_success_rule(self):
        outputs = self.successful_outputs({'decision': 'UNCLEAR', 'blockers': []})
        result = pending_approval(StepInput(
            input={'review_gate_variant': 'baseline'}, previous_step_outputs=outputs))
        self.assertEqual(result.content['result'], 'READY_FOR_HUMAN_REVIEW')

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
