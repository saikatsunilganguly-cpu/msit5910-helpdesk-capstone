"""
Helpdesk Ticket Categorisation & Triage -- minimal working prototype.

This is the lightweight implementation proposed to Dr. Whyte as an
initial version of the Unit 3 design: it does not replace the
process-design scope of Units 1-2, it demonstrates two working
functionalities directly traceable to that design:

  1. Ticket submission -> automatic categorisation & priority/routing
     (Ticket Submission Interface + Categorisation Module + Triage
     and Assessment Module from Document 1's architecture)
  2. An RBAC-gated queue view (Security and Governance Layer / RBAC
     from Document 1 -- agents cannot see security-sensitive ticket
     detail; only the identity_management role can)

Every action is written to the audit_log table, matching the
"audit logging" safeguard described in both documents.
"""
from flask import Flask, request, render_template, redirect, url_for, session

from models import init_db, get_connection, log_action
from categorization import categorize_ticket

app = Flask(__name__)
app.secret_key = "dev-only-secret-key-not-for-production"  # fine for a local capstone demo


@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for("submit_ticket"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        conn = get_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user is None:
            return render_template("login.html", error="Unknown user. Try 'agent1' or 'idmgmt1'.")
        session["username"] = user["username"]
        session["role"] = user["role"]
        log_action(username, "login")
        return redirect(url_for("submit_ticket"))
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    if "username" in session:
        log_action(session["username"], "logout")
    session.clear()
    return redirect(url_for("login"))


@app.route("/submit", methods=["GET", "POST"])
def submit_ticket():
    if "username" not in session:
        return redirect(url_for("login"))

    result = None
    if request.method == "POST":
        description = request.form["description"].strip()
        if not description:
            # Unit 7 fix (found by tests ST-09 and ST-10): empty tickets used to be stored.
            return render_template(
                "submit.html", username=session["username"], role=session["role"],
                result=None, error="Please describe the issue before submitting.",
            ), 400
        category, priority, sensitive = categorize_ticket(description)

        conn = get_connection()
        conn.execute(
            "INSERT INTO tickets (description, category, priority, security_sensitive, submitted_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (description, category, priority, int(sensitive), session["username"]),
        )
        ticket_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        log_action(session["username"], "submit_ticket", ticket_id)
        result = {"category": category, "priority": priority, "sensitive": sensitive, "id": ticket_id}

    return render_template("submit.html", username=session["username"], role=session["role"], result=result)


@app.route("/queue")
def queue():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    # Unit 7 fix (found by test ST-11): created_at has one-second resolution, so tickets
    # submitted in the same second tied; id DESC makes "newest first" reliable.
    tickets = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC, id DESC").fetchall()
    conn.close()

    log_action(session["username"], "view_queue")

    # RBAC enforcement: agents see every ticket, but the description of a
    # security-sensitive ticket (e.g. password/account access) is masked
    # unless the viewer is identity_management. This mirrors the
    # "account-recovery details" example from Document 1, Section 4.
    is_privileged = session["role"] == "identity_management"
    visible_tickets = []
    for t in tickets:
        row = dict(t)
        if row["security_sensitive"] and not is_privileged:
            row["description"] = "[restricted -- identity management role required]"
        visible_tickets.append(row)

    return render_template(
        "queue.html", username=session["username"], role=session["role"], tickets=visible_tickets
    )


if __name__ == "__main__":
    init_db()
    # use_reloader=False: the reloader watches the whole directory, and since
    # helpdesk.db (the SQLite file) is rewritten on every ticket/login/audit
    # action, it was triggering constant restarts. Not needed for a demo run.
    app.run(debug=True, port=5000, use_reloader=False)
