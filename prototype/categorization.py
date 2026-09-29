"""
Rule-based categorisation and triage logic.

Document 2 explicitly justifies a rule-based approach over machine learning
(citing Revina et al., 2020 and Wahba et al., 2020 -- simpler methods matched
or outperformed heavier ones for ticket classification). This module keeps
that same design choice: plain keyword matching, no ML model, fully
explainable -- a category's priority can be traced directly to the rule
that produced it, which matters for the "fairness through transparent,
reviewable categorization" argument in Document 1.
"""
from models import get_connection


def categorize_ticket(description: str):
    """
    Match a ticket description against the category keyword table.
    Returns (category_name, priority, security_sensitive) for the best match,
    or a fallback "Uncategorized" result if nothing matches -- this fallback
    is itself part of the fairness design: uncertain tickets get routed to
    human review rather than being forced into a guessed category.
    """
    description_lower = description.lower()

    conn = get_connection()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()

    best_match = None
    best_match_count = 0

    for cat in categories:
        keywords = [k.strip() for k in cat["keywords"].split(",")]
        match_count = sum(1 for k in keywords if k in description_lower)
        if match_count > best_match_count:
            best_match_count = match_count
            best_match = cat

    if best_match is None:
        # No keyword matched -- route to human review rather than guess.
        return "Uncategorized - Needs Human Review", "Medium", False

    return best_match["name"], best_match["default_priority"], bool(best_match["security_sensitive"])
