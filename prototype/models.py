"""
Database layer for the helpdesk ticket categorisation/triage prototype.

This maps directly onto the architecture in Document 1:
- "Category and Priority Data Store" -> categories table
- Ticket Submission Interface output -> tickets table
- Security and Governance Layer (audit logging) -> audit_log table
- RBAC -> users table with a role column
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "helpdesk.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed reference data. Safe to run multiple times."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            keywords TEXT NOT NULL,        -- comma-separated trigger words
            default_priority TEXT NOT NULL, -- Low / Medium / High / Critical
            security_sensitive INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            security_sensitive INTEGER NOT NULL DEFAULT 0,
            submitted_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL  -- 'agent' or 'identity_management'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            ticket_id INTEGER,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Seed categories -- five standard categories per FR1 in Document 1.
    # security_sensitive=1 marks categories that trigger the RBAC restriction
    # (only identity_management role can see full ticket detail), matching
    # the "account-recovery details" example in Document 1's Section 4.
    categories = [
        ("Password / Account Access", "password,locked out,login,mfa,account,password reset,reset my password,reset your password,forgot password", "High", 1),
        ("Hardware Issue", "laptop,monitor,keyboard,mouse,printer,device,hardware", "Medium", 0),
        ("Software / Application Error", "crash,error,bug,freeze,application,software,install", "Medium", 0),
        ("Network Connectivity", "wifi,network,vpn,connection,internet,offline", "High", 0),
        ("Access Request / Permissions", "access,permission,folder,shared drive,role,grant", "Medium", 1),
    ]
    for name, keywords, priority, sensitive in categories:
        cur.execute(
            "INSERT OR IGNORE INTO categories (name, keywords, default_priority, security_sensitive) "
            "VALUES (?, ?, ?, ?)",
            (name, keywords, priority, sensitive),
        )

    # Seed two demo users -- one per RBAC role described in Document 1.
    users = [("agent1", "agent"), ("idmgmt1", "identity_management")]
    for username, role in users:
        cur.execute("INSERT OR IGNORE INTO users (username, role) VALUES (?, ?)", (username, role))

    conn.commit()
    conn.close()


def log_action(username, action, ticket_id=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_log (username, action, ticket_id) VALUES (?, ?, ?)",
        (username, action, ticket_id),
    )
    conn.commit()
    conn.close()
