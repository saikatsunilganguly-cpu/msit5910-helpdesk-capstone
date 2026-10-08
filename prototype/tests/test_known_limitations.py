"""
Known limitations (KL-xx). Each test states what a production system SHOULD do and is
marked xfail (expected failure), so the limitation is documented, visible in every test run
and flagged automatically (strict mode) if it is ever fixed. See Chapter 5 of the report.
"""
import pytest


@pytest.mark.xfail(strict=True, reason="Known limitation: the demo login has no password check.")
def test_kl01_login_should_require_a_password(client):
    """KL-01: logging in with only a username should not create a session."""
    client.post("/login", data={"username": "idmgmt1"})
    with client.session_transaction() as s:
        assert "username" not in s


@pytest.mark.xfail(strict=True, reason="Known limitation: keyword ties are resolved by category order.")
def test_kl02_offline_laptop_should_be_a_network_ticket(app_module):
    """KL-02: 'laptop' and 'offline' tie 1-1 and the lower category id wins, so this is misclassified."""
    from categorization import categorize_ticket
    assert categorize_ticket("My laptop shows offline even though others are connected")[0] == "Network Connectivity"


@pytest.mark.xfail(strict=True, reason="Known limitation: no CSRF protection on form posts.")
def test_kl03_form_post_without_a_csrf_token_should_be_refused(client, login, submit):
    """KL-03: a ticket posted without an anti-forgery token should be refused (400 or 403)."""
    login("agent1")
    assert submit("My laptop keyboard is not working").status_code in (400, 403)
