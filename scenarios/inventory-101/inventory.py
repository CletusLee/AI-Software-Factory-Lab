"""Small inventory event ledger used to evaluate project-specific reviews."""


class InventoryLedger:
    def __init__(self):
        self.entries = {}

    def receive(self, event_id, sku, quantity):
        payload = (sku, quantity)
        if event_id in self.entries:
            if self.entries[event_id] != payload:
                raise ValueError(f'conflicting inventory event {event_id!r}')
            return self.entries[event_id]
        self.entries[event_id] = payload
        return payload
