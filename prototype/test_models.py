"""
Unit tests for models.py -- the database layer described in Document 1
as the "Category and Priority Data Store", the tickets table, the
users table (RBAC roles), and the audit_log table (Security and
Governance Layer).

White-box unit tests: they check schema creation, seed-data content,
idempotency of init_db(), and the audit-logging side effect of
log_action(), all with direct knowledge of the underlying SQL.
"""
import os
import pytest
from models import init_db, get_connection, log_action, DB_PATH


@pytest.fixture(autouse=True)
def fresh_database():
    if DB_PATH.exists():
        os.remove(DB_PATH)
    yield
    if DB_PATH.exists():
        os.remove(DB_PATH)


def test_init_db_creates_all_four_tables():
    init_db()
    conn = get_connection()
    tables = {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    conn.close()
    assert {"categories", "tickets", "users", "audit_log"}.issubset(tables)


def test_init_db_seeds_exactly_five_categories():
    init_db()
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM categories").fetchone()["c"]
    conn.close()
    assert count == 5  # FR1: at least five standard ticket categories


def test_init_db_seeds_exactly_two_demo_users():
    init_db()
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    conn.close()
    assert count == 2  # one 'agent' role, one 'identity_management' role


def test_seeded_roles_match_rbac_design():
    init_db()
    conn = get_connection()
    roles = {row["username"]: row["role"] for row in conn.execute("SELECT username, role FROM users")}
    conn.close()
    assert roles == {"agent1": "agent", "idmgmt1": "identity_management"}


def test_init_db_is_idempotent():
    # Document 1 notes init_db() should be "safe to run multiple times".
    # Running it twice must not duplicate seed rows (INSERT OR IGNORE).
    init_db()
    init_db()
    init_db()
    conn = get_connection()
    cat_count = conn.execute("SELECT COUNT(*) AS c FROM categories").fetchone()["c"]
    user_count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    conn.close()
    assert cat_count == 5
    assert user_count == 2


def test_log_action_inserts_expected_row():
    init_db()
    log_action("agent1", "login")
    conn = get_connection()
    row = conn.execute(
        "SELECT username, action, ticket_id FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row["username"] == "agent1"
    assert row["action"] == "login"
    assert row["ticket_id"] is None


def test_log_action_records_ticket_id_when_provided():
    init_db()
    log_action("agent1", "submit_ticket", ticket_id=7)
    conn = get_connection()
    row = conn.execute(
        "SELECT ticket_id FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row["ticket_id"] == 7


def test_security_sensitive_categories_flagged_correctly():
    # Document 1, Section 4: "account-recovery details" example --
    # Password/Account Access and Access Request/Permissions should be
    # the two categories flagged security_sensitive=1; the other three
    # should not be.
    init_db()
    conn = get_connection()
    flagged = {row["name"] for row in conn.execute(
        "SELECT name FROM categories WHERE security_sensitive = 1"
    )}
    conn.close()
    assert flagged == {"Password / Account Access", "Access Request / Permissions"}
