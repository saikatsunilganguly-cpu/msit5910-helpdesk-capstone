"""
Accuracy check for the rule-based categoriser (Unit 6, Part B).

Reads the 50 hand-labelled tickets in test_tickets.csv, runs each one through
categorize_ticket(), and reports overall and per-category accuracy.

Safe to run: it uses a temporary database and never touches helpdesk.db.
Run from the prototype folder:   python evaluation/measure_accuracy.py
"""
import csv
import json
import platform
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))          # the prototype folder (next to app.py)

import models                                  # noqa: E402

CATEGORIES = [
    "Password / Account Access",
    "Hardware Issue",
    "Software / Application Error",
    "Network Connectivity",
    "Access Request / Permissions",
]


def warn_if_old_keywords():
    """The v0.2.0 fix replaced the bare keyword 'reset'. Warn if it is still present."""
    conn = models.get_connection()
    rows = conn.execute("SELECT name, keywords FROM categories").fetchall()
    conn.close()
    for row in rows:
        if "reset" in [k.strip() for k in row["keywords"].split(",")]:
            print("WARNING: models.py still has the bare keyword 'reset' (pre-fix version).")
            print("         Results will differ from the Unit 6 report. Use models.py from tag v0.2.0 or later.")
            print()


def main():
    tickets = list(csv.DictReader(open(HERE / "test_tickets.csv", newline="", encoding="utf-8")))
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        models.DB_PATH = Path(tmp) / "eval.db"      # temporary database, not helpdesk.db
        models.init_db()
        warn_if_old_keywords()
        from categorization import categorize_ticket

        results = []
        for t in tickets:
            predicted, _priority, _sensitive = categorize_ticket(t["description"])
            results.append((t["description"], t["expected_category"], predicted))

    correct = sum(1 for _, e, p in results if e == p)
    total = len(results)
    per_cat = defaultdict(lambda: {"correct": 0, "total": 0})
    for _, e, p in results:
        per_cat[e]["total"] += 1
        per_cat[e]["correct"] += int(e == p)
    misses = [[d, e, p] for d, e, p in results if e != p]

    print(f"Platform: {platform.platform()} | Python {platform.python_version()}")
    print()
    print(f"Overall accuracy: {correct}/{total} = {correct / total * 100:.1f}%")
    print()
    print(f"{'Category':35s} {'Correct':>8s} {'Total':>6s} {'Accuracy':>9s}")
    for cat in CATEGORIES:
        c, n = per_cat[cat]["correct"], per_cat[cat]["total"]
        print(f"{cat:35s} {c:8d} {n:6d} {c / n * 100:8.1f}%")
    print()
    print("Misclassified cases:")
    for d, e, p in misses:
        print(f"  Expected: {e!r:35s} Got: {p!r:35s} | {d!r}")
    if not misses:
        print("  none")

    with open(out_dir / "accuracy_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "accuracy_pct": correct / total * 100, "correct": correct, "total": total,
            "per_category": {c: per_cat[c] for c in CATEGORIES},
            "misclassified": misses,
            "platform": platform.platform(), "python": platform.python_version(),
        }, f, indent=2)
    print()
    print(f"Saved: {out_dir / 'accuracy_results.json'}")


if __name__ == "__main__":
    main()
