"""Local QA oracle for a payment webhook retry demonstration."""
import unittest

from payment_demo import PaymentLedger


class PaymentLedgerTests(unittest.TestCase):
    def test_retry_does_not_duplicate_entry(self):
        ledger = PaymentLedger()
        ledger.receive('event-1', 100)
        ledger.receive('event-1', 100)
        self.assertEqual(ledger.entries, {'event-1': 100})

    def test_distinct_events_are_recorded(self):
        ledger = PaymentLedger()
        ledger.receive('event-1', 100)
        ledger.receive('event-2', 200)
        self.assertEqual(ledger.entries, {'event-1': 100, 'event-2': 200})

    def test_same_event_with_conflicting_amount_is_rejected(self):
        ledger = PaymentLedger()
        ledger.receive('event-1', 100)
        with self.assertRaisesRegex(ValueError, 'conflicting payload'):
            ledger.receive('event-1', 120)
        self.assertEqual(ledger.entries, {'event-1': 100})


if __name__ == '__main__':
    unittest.main(verbosity=2)
