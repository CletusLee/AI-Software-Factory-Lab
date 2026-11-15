import unittest
from pay482_evidence import classify


class EvidenceTests(unittest.TestCase):
    def test_scenario_results_and_missing_evidence(self):
        for scenario, expected in [('stale', 'NOT READY'), ('timeout', 'UNKNOWN'),
                                   ('fail', 'NOT READY'), ('ready', 'READY')]:
            self.assertEqual(classify('PAY-482 scenario ' + scenario, 'PASS')[1], expected)
        self.assertEqual(classify('ready', 'UNKNOWN')[1], 'UNKNOWN')
        self.assertEqual(classify('ready', 'FAIL')[1], 'NOT READY')
        self.assertEqual(classify('ready stale', 'PASS')[1], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
