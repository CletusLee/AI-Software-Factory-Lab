"""Small in-memory payment ledger for the local demonstration."""


class PaymentLedger:
    def __init__(self):
        self.entries = {}

    def receive(self, event_id, amount):
        if event_id in self.entries:
            if self.entries[event_id] != amount:
                raise ValueError(f'conflicting payload for event {event_id!r}')
            return self.entries[event_id]
        self.entries[event_id] = amount
        return amount
