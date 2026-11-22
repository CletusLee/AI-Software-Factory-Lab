"""Inventory retry acceptance checks."""
import unittest

from inventory import InventoryLedger


class InventoryLedgerTests(unittest.TestCase):
    def test_identical_retry_is_idempotent(self):
        ledger = InventoryLedger()
        ledger.receive('sync-1', 'SKU-1', 4)
        ledger.receive('sync-1', 'SKU-1', 4)
        self.assertEqual(ledger.entries, {'sync-1': ('SKU-1', 4)})

    def test_conflicting_payload_is_rejected_without_changing_original(self):
        ledger = InventoryLedger()
        ledger.receive('sync-1', 'SKU-1', 4)
        with self.assertRaisesRegex(ValueError, 'conflicting inventory event'):
            ledger.receive('sync-1', 'SKU-1', 7)
        self.assertEqual(ledger.entries, {'sync-1': ('SKU-1', 4)})
