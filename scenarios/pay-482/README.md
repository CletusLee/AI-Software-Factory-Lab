# PAY-482: Payment webhook retries

This work item is an input to the shared `software-delivery` workflow. A payment service accepted `event-1`, then the provider retried the same event ID with a different amount. The original ledger compared only event IDs and silently returned the old amount without exposing the conflict.

`work-item.json` defines the requirements, acceptance criteria, permitted files, and candidate change. `baseline/payment_demo.py` preserves the faulty version, where the regression test first fails. Each run applies the candidate change in its own isolated workspace without overwriting the read-only source. The shared example `payment_demo.py` also contains the fix: retries with the same payload remain idempotent, while a different payload raises `ValueError` and preserves the existing entry.

Run `python -m unittest -v test_payment_demo` from this directory. The tests cover sequential retries, distinct events, and conflicting amounts for the same ID. Concurrency, database transactions, webhook signatures, and production release require further verification. Ticket, external CI, and approval states are local simulated data. Cross-POC expected results are in `benchmark/pay-482-cases.json`.
