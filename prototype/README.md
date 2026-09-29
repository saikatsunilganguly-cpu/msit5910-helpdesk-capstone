# Helpdesk Ticket Categorisation & Triage — Prototype

Minimal working implementation of the core logic from Document 1
(System Architecture) and Document 2 (Technical Report):
rule-based ticket categorisation/triage, and an RBAC-gated ticket queue.

## Run it

```
pip install -r requirements.txt
python app.py
```
Then visit http://127.0.0.1:5000 and log in as `agent1` or `idmgmt1`.

## Run the unit tests

```
pytest -v --cov=categorization --cov=models --cov-report=term-missing
```

19 tests, 100% statement coverage on `categorization.py` and `models.py`.

## Files

- `app.py` — Flask routes (submission, queue, RBAC enforcement)
- `categorization.py` — rule-based categorisation core logic
- `models.py` — SQLite schema, seed data, audit logging
- `test_categorization.py`, `test_models.py` — PyTest unit tests

## Known-issue fix (v0.2.0)

Unit testing discovered that a generic `"reset"` keyword in the
Password/Account Access category caused false positives on unrelated
hardware tickets (e.g. "reset my monitor settings"). Fixed by using
specific phrases instead. See `test_categorization.py` for the
regression tests that document and lock in this fix.
