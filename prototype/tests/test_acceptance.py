"""
Acceptance tests (AT-xx): each test checks one requirement or success criterion from the
Unit 3 design documents (FR = functional requirement, NFR = non-functional requirement).
"""
import csv
import statistics
import time
from pathlib import Path

import pytest

MASK = b"[restricted -- identity management role required]"

SAMPLES = [
    ("I am locked out of my account and need a password reset", "Password / Account Access", 1),
    ("My laptop keyboard is not working", "Hardware Issue", 0),
    ("The application keeps crashing when I open it", "Software / Application Error", 0),
    ("I cannot connect to the office wifi", "Network Connectivity", 0),
    ("I need permission to the shared drive for the finance folder", "Access Request / Permissions", 1),
]


def test_at01_fr1_five_standard_categories_work_end_to_end(login, submit, db):
    """AT-01 (FR1): one representative ticket for each of the five categories is categorised correctly."""
    login("agent1")
    for text, _, _ in SAMPLES:
        submit(text)
    stored = [r["category"] for r in db("SELECT category FROM tickets ORDER BY id")]
    assert stored == [category for _, category, _ in SAMPLES]


def test_at02_fr4_sensitive_categories_are_flagged(login, submit, db):
    """AT-02 (FR4): password and access-request tickets are flagged security-sensitive; the others are not."""
    login("agent1")
    for text, _, _ in SAMPLES:
        submit(text)
    flags = [r["security_sensitive"] for r in db("SELECT security_sensitive FROM tickets ORDER BY id")]
    assert flags == [flag for _, _, flag in SAMPLES]


def test_at03_fr7_role_based_access_control(client, login, submit):
    """AT-03 (FR7): an agent sees two masked tickets and one readable one; identity_management sees all three."""
    login("agent1")
    submit(SAMPLES[0][0])
    submit(SAMPLES[4][0])
    submit(SAMPLES[1][0])
    agent_view = client.get("/queue").data
    assert agent_view.count(MASK) == 2 and b"keyboard" in agent_view
    client.get("/logout")
    login("idmgmt1")
    full_view = client.get("/queue").data
    assert MASK not in full_view and b"locked out" in full_view and b"finance folder" in full_view


def test_at04_fr7_audit_trail_records_the_whole_session(client, login, submit, db):
    """AT-04 (FR7): login, submit, queue view and logout are all recorded, in order, with a timestamp."""
    login("agent1")
    submit(SAMPLES[1][0])
    client.get("/queue")
    client.get("/logout")
    rows = db("SELECT action, timestamp FROM audit_log ORDER BY id")
    assert [r["action"] for r in rows] == ["login", "submit_ticket", "view_queue", "logout"]
    assert all(r["timestamp"] for r in rows)


def test_at05_categorisation_clarity_on_the_labelled_test_set(app_module):
    """AT-05 (evaluation criterion 'categorisation clarity'): at least 90% of the 50 labelled tickets are categorised correctly."""
    path = Path(__file__).resolve().parent.parent / "evaluation" / "test_tickets.csv"
    if not path.exists():
        pytest.skip("evaluation/test_tickets.csv not found")
    from categorization import categorize_ticket
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    correct = sum(1 for r in rows if categorize_ticket(r["description"])[0] == r["expected_category"])
    assert len(rows) == 50 and correct / len(rows) >= 0.90


def test_at06_nfr_submission_responds_quickly(login, submit):
    """AT-06 (performance NFR): the median time to submit a ticket is under 100 ms."""
    login("agent1")
    times = []
    for _ in range(30):
        start = time.perf_counter()
        submit("My laptop keyboard is not working")
        times.append((time.perf_counter() - start) * 1000)
    assert statistics.median(times) < 100


def test_at07_uncertain_tickets_are_routed_to_a_human(login, submit, db):
    """AT-07 (fairness NFR): a ticket the rules cannot place is sent for human review instead of being guessed."""
    login("agent1")
    submit("The coffee machine in the break room is broken")
    assert db("SELECT category FROM tickets")[0]["category"].startswith("Uncategorized")
