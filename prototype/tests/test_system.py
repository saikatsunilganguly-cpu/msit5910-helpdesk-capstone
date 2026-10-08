"""
System tests (ST-xx): complete user journeys through the running application, including
access control, error handling and basic security checks (input handling, injection).
"""
from pathlib import Path

PASSWORD_TICKET = "I am locked out of my account and need a password reset"
HARDWARE_TICKET = "My laptop keyboard is not working"
MASK = b"[restricted -- identity management role required]"


def _location(response):
    return response.headers.get("Location", "")


def test_st01_submit_page_requires_login(client):
    """ST-01: an anonymous visitor to /submit is redirected to the login page."""
    r = client.get("/submit")
    assert r.status_code == 302 and _location(r).endswith("/login")


def test_st02_queue_requires_login(client):
    """ST-02: an anonymous visitor to /queue is redirected to the login page."""
    r = client.get("/queue")
    assert r.status_code == 302 and _location(r).endswith("/login")


def test_st03_home_redirects_by_login_state(client, login):
    """ST-03: / goes to login when anonymous and to the submit page once logged in."""
    assert _location(client.get("/")).endswith("/login")
    login("agent1")
    assert _location(client.get("/")).endswith("/submit")


def test_st04_unknown_user_cannot_log_in(client):
    """ST-04: an unknown username gets the login page back, no session, and the error message."""
    r = client.post("/login", data={"username": "nobody"})
    assert r.status_code == 200 and b"Unknown user" in r.data
    with client.session_transaction() as s:
        assert "username" not in s


def test_st05_agent_sees_sensitive_ticket_masked(client, login, submit):
    """ST-05: end to end, an agent's queue hides the detail of a security-sensitive ticket."""
    login("agent1")
    submit(PASSWORD_TICKET)
    page = client.get("/queue")
    assert MASK in page.data and b"locked out of my account" not in page.data


def test_st06_identity_management_sees_full_detail(client, login, submit):
    """ST-06: the same ticket is fully visible to the identity_management role."""
    login("agent1")
    submit(PASSWORD_TICKET)
    client.get("/logout")
    login("idmgmt1")
    page = client.get("/queue")
    assert b"locked out of my account" in page.data and MASK not in page.data


def test_st07_agent_sees_non_sensitive_ticket_in_full(client, login, submit):
    """ST-07: non-sensitive tickets are never masked."""
    login("agent1")
    submit(HARDWARE_TICKET)
    assert b"keyboard" in client.get("/queue").data


def test_st08_logout_ends_the_session(client, login):
    """ST-08: after logout the protected pages redirect to login again."""
    login("agent1")
    client.get("/logout")
    assert _location(client.get("/queue")).endswith("/login")
    assert _location(client.get("/submit")).endswith("/login")


def test_st09_empty_description_is_rejected(login, submit, db):
    """ST-09: an empty description is refused (HTTP 400) and nothing is stored."""
    login("agent1")
    r = submit("")
    assert r.status_code == 400 and b"Please describe the issue" in r.data
    assert db("SELECT COUNT(*) AS n FROM tickets")[0]["n"] == 0


def test_st10_whitespace_only_description_is_rejected(login, submit, db):
    """ST-10: a description of only spaces is refused and nothing is stored."""
    login("agent1")
    r = submit("   \t  ")
    assert r.status_code == 400
    assert db("SELECT COUNT(*) AS n FROM tickets")[0]["n"] == 0


def test_st11_queue_lists_newest_ticket_first(client, login, submit, rendered):
    """ST-11: tickets submitted within the same second still appear newest first."""
    login("agent1")
    for text in ("My laptop keyboard is not working", "I cannot connect to the office wifi", "The application keeps crashing when I open it"):
        submit(text)
    client.get("/queue")
    ids = [t["id"] for t in [c for n, c in rendered if n == "queue.html"][-1]["tickets"]]
    assert ids == [3, 2, 1]


def test_st12_script_tags_are_escaped_when_displayed(client, login, submit):
    """ST-12: HTML typed into a ticket is shown as text, not executed (cross-site scripting check)."""
    login("agent1")
    submit("keyboard broken <script>alert('x')</script>")
    page = client.get("/queue")
    assert b"<script>alert" not in page.data and b"&lt;script&gt;" in page.data


def test_st13_sql_injection_text_is_stored_literally(client, login, submit, db):
    """ST-13: SQL meta-characters in a ticket are treated as data; the tables stay intact."""
    login("agent1")
    payload = "keyboard'); DROP TABLE tickets;--"
    assert submit(payload).status_code == 200
    rows = db("SELECT description FROM tickets")
    assert rows == [{"description": payload}]


def test_st14_very_long_description_is_handled(login, submit, db):
    """ST-14: a 5,000-character description is accepted without an error."""
    login("agent1")
    text = "keyboard " * 556
    assert submit(text).status_code == 200
    assert len(db("SELECT description FROM tickets")[0]["description"]) >= 4900


def test_st15_unicode_text_round_trips(login, submit, db):
    """ST-15: non-English characters are stored and read back unchanged."""
    login("agent1")
    text = "Mi teclado no funciona \u952e\u76d8 caf\u00e9"
    submit(text)
    assert db("SELECT description FROM tickets")[0]["description"] == text


def test_st16_malformed_requests_get_client_errors_not_server_errors(client, login):
    """ST-16: a missing form field returns 400 and a wrong method returns 405, never a 500."""
    login("agent1")
    assert client.post("/submit", data={}).status_code == 400
    assert client.post("/queue").status_code == 405


def test_st17_login_page_loads(client):
    """ST-17: the login page is served to an anonymous visitor."""
    r = client.get("/login")
    assert r.status_code == 200 and b"agent1" in r.data
