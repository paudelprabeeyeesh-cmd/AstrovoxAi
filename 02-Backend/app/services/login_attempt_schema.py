"""Canonical schema for the login_attempts table.

Two modules write to this table: ``app/services/auth/auth.py`` (the
brute-force lockout in the request path) and
``app/services/auth_service.py`` (the legacy audit insert). They had each
created the table with a different column set, so whichever module ran
first won and the other one failed at query time with
"table login_attempts has no column named lockout_until".

The table has no init path at all: neither ``database/connection.py`` nor
the infrastructure engine creates it, so on a fresh install the lockout
control silently never applied.

Both modules must import the CREATE statement from here.
"""
from __future__ import annotations

CREATE_LOGIN_ATTEMPTS_TABLE = """
CREATE TABLE IF NOT EXISTS login_attempts (
    id TEXT PRIMARY KEY,
    ip TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    success INTEGER NOT NULL DEFAULT 0,
    lockout_until TEXT,
    created_at TEXT NOT NULL
)
"""

CREATE_LOGIN_ATTEMPTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_login_attempts_window
    ON login_attempts (ip, email, success, created_at)
"""

# Baseline migration: add the columns an older table may be missing.
# CREATE TABLE IF NOT EXISTS is a no-op when the table already exists, so
# an install created by the narrower legacy schema needs ALTERs.
ALTER_LOGIN_ATTEMPTS_ADD_EMAIL = (
    "ALTER TABLE login_attempts ADD COLUMN email TEXT NOT NULL DEFAULT ''"
)
ALTER_LOGIN_ATTEMPTS_ADD_LOCKOUT = (
    "ALTER TABLE login_attempts ADD COLUMN lockout_until TEXT"
)


def ensure_login_attempts_table(conn) -> None:
    """Create or migrate the table in place on the given connection.

    Idempotent: safe to call on every write. Each ALTER catches the
    "duplicate column name" error so a re-run after a successful migration
    is a no-op rather than an exception.

    The statements are wrapped in ``text()`` because the connection is a
    SQLAlchemy Session, which rejects a bare string SQL argument.
    """
    from sqlalchemy import text

    conn.execute(text(CREATE_LOGIN_ATTEMPTS_TABLE))
    conn.execute(text(CREATE_LOGIN_ATTEMPTS_INDEX))
    for alter in (ALTER_LOGIN_ATTEMPTS_ADD_EMAIL, ALTER_LOGIN_ATTEMPTS_ADD_LOCKOUT):
        try:
            conn.execute(text(alter))
        except Exception:  # noqa: BLE001 - duplicate column means already migrated
            pass
