"""
Integration tests (IT-xx): the Flask routes, the categorisation module and the SQLite
database working together. Each test drives the real routes and then checks what the
database actually holds.
"""
PASSWORD_TICKET = "I am locked out of my account and need a password reset"
HARDWARE_TICKET = "My laptop keyboard is not working"
UNMATCHED_TICKET = "The coffee machine in the break room is broken"


def test_it01_submit_stores_sensitive_ticket_with_categorisation_result(login, submit, db):
    """IT-01: a password ticket is stored as Password / Account Access, High, security-sensitive."""
    login("agent1")
    assert submit(PASSWORD_TICKET).status_code == 200
    row = db("SELECT * FROM tickets")[0]
    assert (row["category"], row["priority"], row["security_sensitive"]) == ("Password / Account Access", "High", 1)
    assert row["submitted_by"] == "agent1" and row["status"] == "Open"


def test_it02_submit_stores_non_sensitive_ticket(login, submit, db):
    """IT-02: a hardware ticket is stored as Hardware Issue, Medium, not security-sensitive."""
    login("agent1")
    submit(HARDWARE_TICKET)
    row = db("SELECT * FROM tickets")[0]
    assert (row["category"], row["priority"], row["security_sensitive"]) == ("Hardware Issue", "Medium", 0)


def test_it03_unmatched_ticket_goes_to_human_review(login, submit, db):
    """IT-03: text that matches no keyword is stored under the human-review fallback, not guessed."""
    login("agent1")
    submit(UNMATCHED_TICKET)
    assert db("SELECT category FROM tickets")[0]["category"] == "Uncategorized - Needs Human Review"


def test_it04_submit_writes_audit_entry_linked_to_the_ticket(login, submit, db):
    """IT-04: submitting writes one audit entry that names the user and the new ticket id."""
    login("agent1")
    submit(HARDWARE_TICKET)
    ticket_id = db("SELECT id FROM tickets")[0]["id"]
    audit = db("SELECT username, ticket_id FROM audit_log WHERE action = 'submit_ticket'")
    assert audit == [{"username": "agent1", "ticket_id": ticket_id}]


def test_it05_login_and_logout_are_audited(client, login, db):
    """IT-05: login and logout each write an audit entry for the user."""
    login("agent1")
    client.get("/logout")
    actions = [r["action"] for r in db("SELECT action FROM audit_log WHERE username = 'agent1' ORDER BY id")]
    assert actions == ["login", "logout"]


def test_it06_viewing_the_queue_is_audited(client, login, db):
    """IT-06: opening the queue writes a view_queue audit entry."""
    login("agent1")
    client.get("/queue")
    assert [r["action"] for r in db("SELECT action FROM audit_log WHERE action = 'view_queue'")] == ["view_queue"]


def test_it07_session_carries_username_and_role(client, login):
    """IT-07: after login the session holds the username and the role read from the users table."""
    login("idmgmt1")
    with client.session_transaction() as s:
        assert (s["username"], s["role"]) == ("idmgmt1", "identity_management")


def test_it08_submitted_ticket_appears_in_the_queue(client, login, submit):
    """IT-08: data written by /submit is read back by /queue (persistence across requests)."""
    login("agent1")
    submit(HARDWARE_TICKET)
    page = client.get("/queue")
    assert page.status_code == 200 and b"keyboard" in page.data


def test_it09_submitted_by_follows_the_logged_in_user(client, login, submit, db):
    """IT-09: each ticket records the user who was logged in when it was submitted."""
    login("agent1")
    submit(HARDWARE_TICKET)
    client.get("/logout")
    login("idmgmt1")
    submit("I cannot connect to the office wifi")
    assert [r["submitted_by"] for r in db("SELECT submitted_by FROM tickets ORDER BY id")] == ["agent1", "idmgmt1"]
