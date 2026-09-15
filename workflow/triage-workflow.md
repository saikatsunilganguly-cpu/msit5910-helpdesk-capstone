# Triage Workflow

1. End User submits a ticket via the Ticket Submission Interface.
2. Categorisation Module maps the request to a standard category and writes
   to the Category and Priority Data Store.
3. Triage and Assessment Module evaluates impact, urgency, and security flags.
4. Assignment and Escalation Module routes the ticket to a queue or role.
5. Ticket Resolution and Status Update.
6. Reporting and Analytics Module aggregates workload and performance data.

The Security and Governance Layer (RBAC, audit logging, encryption, data
minimisation, retention controls) applies across every step above.
