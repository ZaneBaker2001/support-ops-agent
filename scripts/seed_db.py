from pathlib import Path

from sqlalchemy import create_engine, text

DB_PATH = Path("./data/support.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

DDL = """
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  category TEXT NOT NULL,
  priority TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  owner TEXT,
  status TEXT NOT NULL
);
"""

ROWS = [
    ("2026-04-08 10:12:00", "auth", "high", "Password reset emails delayed",
     "Users report delayed reset links after requesting password reset.", "alice", "open"),
    ("2026-04-08 12:40:00", "auth", "high", "Password reset token invalid",
     "Reset token expired immediately for some enterprise tenants.", "bob", "investigating"),
    ("2026-04-07 08:20:00", "billing", "medium", "Invoice PDF download timeout",
     "Customers unable to download invoices intermittently.", "cathy", "open"),
    ("2026-04-06 09:15:00", "auth", "critical", "SSO login loop for SAML users",
     "After IdP redirect, users land back on login page.", "david", "resolved"),
    ("2026-04-06 11:00:00", "auth", "medium", "Password reset emails in spam",
     "Reset emails delivered but flagged by recipient mail systems.", "alice", "open"),
    ("2026-04-05 16:30:00", "api", "low", "Webhook retry question",
     "Customer asking how webhook backoff works.", "emma", "closed"),
    ("2026-04-04 14:00:00", "auth", "high", "Password reset unavailable on mobile",
     "Mobile web flow returns generic error after submit.", "frank", "open"),
    ("2026-04-03 07:50:00", "infra", "critical", "Redis latency spike",
     "Latency spike correlated with session lookup failures.", "david", "resolved"),
]

with engine.begin() as conn:
    conn.execute(text(DDL))
    existing = conn.execute(text("SELECT COUNT(*) AS count FROM tickets")).scalar_one()
    if existing == 0:
        conn.execute(
            text("""
            INSERT INTO tickets (
              created_at, category, priority, title, description, owner, status
            ) VALUES (
              :created_at, :category, :priority, :title, :description, :owner, :status
            )
            """),
            [
                {
                    "created_at": r[0],
                    "category": r[1],
                    "priority": r[2],
                    "title": r[3],
                    "description": r[4],
                    "owner": r[5],
                    "status": r[6],
                }
                for r in ROWS
            ],
        )

print(f"Database initialized at {DB_PATH}")