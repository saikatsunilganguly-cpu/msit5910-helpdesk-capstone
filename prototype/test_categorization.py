"""
Unit tests for categorization.py -- the core rule-based categorisation
and triage logic described in Document 1 (Categorisation Module,
Triage and Assessment Module) and justified in Document 2 (rule-based
over ML, citing Revina et al., 2020 and Wahba et al., 2020).

These are white-box unit tests: each test targets the internal logic
of categorize_ticket() directly (keyword matching, tie-breaking,
fallback behaviour), with full knowledge of how the function is
implemented, rather than treating it as an opaque black box.
"""
import pytest
import models
from models import init_db
from categorization import categorize_ticket


@pytest.fixture(autouse=True)
def fresh_database(tmp_path, monkeypatch):
    """Give every test a clean, freshly-seeded temporary database (helpdesk.db is never touched)."""
    monkeypatch.setattr(models, "DB_PATH", tmp_path / "unit.db")
    init_db()
    yield


# ---- One test per seeded category (FR1: five standard categories) ----

def test_password_account_access_category():
    category, priority, sensitive = categorize_ticket(
        "I am locked out of my account and need a password reset"
    )
    assert category == "Password / Account Access"
    assert priority == "High"
    assert sensitive is True


def test_hardware_issue_category():
    category, priority, sensitive = categorize_ticket(
        "My laptop keyboard is not working"
    )
    assert category == "Hardware Issue"
    assert priority == "Medium"
    assert sensitive is False


def test_software_application_error_category():
    category, priority, sensitive = categorize_ticket(
        "The application keeps crashing when I open it"
    )
    assert category == "Software / Application Error"
    assert priority == "Medium"
    assert sensitive is False


def test_network_connectivity_category():
    category, priority, sensitive = categorize_ticket(
        "I cannot connect to the office wifi"
    )
    assert category == "Network Connectivity"
    assert priority == "High"
    assert sensitive is False


def test_access_request_permissions_category():
    category, priority, sensitive = categorize_ticket(
        "I need permission to the shared drive for the finance folder"
    )
    assert category == "Access Request / Permissions"
    assert priority == "Medium"
    assert sensitive is True


# ---- Fallback behaviour (fairness: uncertain tickets go to human review) ----

def test_no_keyword_match_falls_back_to_human_review():
    category, priority, sensitive = categorize_ticket(
        "The coffee machine in the break room is broken"
    )
    assert category == "Uncategorized - Needs Human Review"
    assert priority == "Medium"
    assert sensitive is False


def test_empty_description_falls_back_to_human_review():
    category, priority, sensitive = categorize_ticket("")
    assert category == "Uncategorized - Needs Human Review"


# ---- Case sensitivity ----

def test_categorization_is_case_insensitive():
    category, priority, sensitive = categorize_ticket(
        "PASSWORD RESET NEEDED URGENTLY"
    )
    assert category == "Password / Account Access"


# ---- Regression test for a real issue found during testing ----
# The original seed data used a bare "reset" keyword for Password/Account
# Access. Because match_count only counts substring hits, this caused
# false positives on unrelated tickets like "reset my monitor settings",
# which were wrongly categorised as Password/Account Access AND flagged
# security-sensitive. The fix (see models.py) replaced the generic
# "reset" keyword with specific phrases ("password reset", "reset my
# password", etc.). This test locks in that fix: a hardware-only ticket
# that happens to contain the word "reset" must now correctly fall
# through to Hardware Issue instead.

def test_generic_reset_no_longer_misclassified_as_password_category():
    category, priority, sensitive = categorize_ticket(
        "Please reset my monitor settings, the resolution is wrong"
    )
    assert category == "Hardware Issue"
    assert sensitive is False


def test_specific_password_reset_phrase_still_matches_correctly():
    # Guards against over-correcting: legitimate password-reset language
    # must still route to Password/Account Access after the keyword fix.
    category, priority, sensitive = categorize_ticket(
        "I forgot my password and need a password reset"
    )
    assert category == "Password / Account Access"
    assert sensitive is True


def test_more_keyword_matches_wins_over_fewer():
    # "keyboard" and "mouse" (2 Hardware Issue keywords) should outweigh
    # "error" (1 Software/Application Error keyword) in the same ticket,
    # directly exercising the `match_count > best_match_count` comparison.
    category, priority, sensitive = categorize_ticket(
        "My keyboard and mouse have an error and won't respond"
    )
    assert category == "Hardware Issue"
