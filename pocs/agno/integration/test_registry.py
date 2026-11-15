import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integration.registry import load
from integration.export_catalog import workflow_edges, render
from integration import deploy


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'definitions'
        shutil.copytree(Path(__file__).resolve().parents[3] / 'definitions', self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_handoffs_follow_parallel_join_and_do_not_connect_parallel_peers(self):
        reg = load(self.root)
        edges = workflow_edges(reg['workflows']['software-delivery'])
        for peer in ('factory-04', 'factory-06', 'factory-08'):
            self.assertIn(('factory-03', peer), edges)
            for verifier in ('factory-09', 'factory-11', 'factory-20'):
                self.assertIn((peer, verifier), edges)
        for verifier in ('factory-09', 'factory-11', 'factory-20'):
            self.assertIn((verifier, 'factory-10'), edges)
        self.assertNotIn(('factory-04', 'factory-06'), edges)
        steps = reg['workflows']['software-delivery']['steps'][1]['steps']
        names = [step['name'] for step in steps]
        self.assertIn('Apply Candidate Change', names)
        self.assertIn('Candidate Verification', names)
        self.assertNotIn('PAY-482', reg['workflows']['software-delivery']['name'])
        entities, _ = render(reg)
        workflow = next(x for x in entities if x['metadata']['name'] == 'software-delivery')
        self.assertIn('Apply Candidate Change [executor: apply_candidate_change]', workflow['metadata']['description'])
        self.assertIn('Candidate Verification [executor: verify_candidate]', workflow['metadata']['description'])
        coder = next(x for x in entities if x['metadata']['name'] == 'factory-04')
        self.assertIn('component:default/factory-03', coder['spec']['dependsOn'])

    def test_missing_skill_is_rejected(self):
        shutil.rmtree(self.root / 'skills' / 'patch-proposal')
        with self.assertRaisesRegex(ValueError, 'unknown skills'):
            load(self.root)

    def test_revision_changes_with_prompt(self):
        before = load(self.root)['revision']
        prompt = self.root / 'agents' / 'factory-04-coder' / 'prompt.md'
        prompt.write_text(prompt.read_text(encoding='utf-8') + '\n新增指引\n', encoding='utf-8')
        self.assertNotEqual(before, load(self.root)['revision'])

    def test_failed_activation_restores_previous_snapshot(self):
        previous = load(self.root)['revision']
        releases = Path(self.temp.name) / 'releases'
        shutil.copytree(self.root, releases / previous / 'definitions')
        prompt = self.root / 'agents' / 'factory-04-coder' / 'prompt.md'
        prompt.write_text(prompt.read_text(encoding='utf-8') + '\n候選版本\n', encoding='utf-8')
        candidate = load(self.root)['revision']
        shutil.copytree(self.root, releases / candidate / 'definitions')
        active = Path(self.temp.name) / 'active.txt'
        active.write_text(previous, encoding='utf-8')
        with patch.object(deploy, 'RELEASES', releases), patch.object(deploy, 'ACTIVE', active), \
             patch.object(deploy, 'export') as export, patch.object(deploy, 'compose') as compose, \
             patch.object(deploy, 'health', side_effect=RuntimeError('unhealthy')):
            with self.assertRaisesRegex(RuntimeError, 'unhealthy'):
                deploy.activate(candidate, previous)
        self.assertEqual(active.read_text(encoding='utf-8').strip(), previous)
        self.assertEqual(export.call_count, 2)
        self.assertEqual(compose.call_count, 2)


if __name__ == '__main__':
    unittest.main()
