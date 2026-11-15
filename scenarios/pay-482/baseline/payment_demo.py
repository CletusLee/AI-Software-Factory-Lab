"""PAY-482 issue baseline: duplicate IDs silently ignore changed payloads."""


class PaymentLedger:
    def __init__(self):
        self.entries = {}

    def receive(self, event_id, amount):
        if event_id not in self.entries:
            self.entries[event_id] = amount
        return self.entries[event_id]
