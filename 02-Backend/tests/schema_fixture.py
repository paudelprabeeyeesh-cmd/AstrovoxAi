"""Test-schema fixture.

The product's SQL addresses tables that no migration in this repo creates
for a local SQLite database, so every endpoint that reads them failed with
``no such table`` rather than with a product error. The baseline document
records the same finding and recommends supplying the schema from a test
fixture, which is what this module does.

Only the tables the suite exercises are created. Adding a table here is the
right response when a test needs one; the list is deliberately not an
attempt to mirror the full production schema.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

# SQLite-compatible DDL. Types are kept intentionally loose because the
# assertions in this suite concern row shape, not column constraints.
SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL DEFAULT 'New chat',
        model TEXT NOT NULL DEFAULT 'gpt-4',
        folder_id TEXT,
        is_pinned INTEGER NOT NULL DEFAULT 0,
        is_shared INTEGER NOT NULL DEFAULT 0,
        shared_at TEXT,
        shared_with TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_message_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        parts TEXT,
        model_used TEXT,
        tokens_used INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        filename TEXT,
        content_type TEXT,
        size INTEGER,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        content TEXT,
        embedding TEXT,
        metadata TEXT,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY,
        display_name TEXT,
        avatar_url TEXT,
        full_name TEXT,
        bio TEXT,
        website TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        content TEXT,
        importance INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usage_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        model TEXT,
        provider TEXT,
        tokens INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    # The auth service modules (device, magic_link, mfa, oauth, session) query
    # these tables. No statement in the repo creates them, so every one of
    # those calls failed with "no such table" once the modules were reachable.
    """
    CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT,
        device_type TEXT,
        platform TEXT,
        browser TEXT,
        fingerprint TEXT,
        last_seen_at TEXT,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS magic_links (
        id TEXT PRIMARY KEY,
        email TEXT,
        token_hash TEXT,
        used INTEGER NOT NULL DEFAULT 0,
        expires_at TEXT,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mfa_secrets (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        secret TEXT,
        enabled INTEGER NOT NULL DEFAULT 0,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mfa_backup_codes (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        code_hash TEXT,
        used INTEGER NOT NULL DEFAULT 0,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS oauth_accounts (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        provider TEXT,
        provider_user_id TEXT,
        access_token TEXT,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        session_token TEXT,
        refresh_token TEXT,
        expires_at TEXT,
        last_activity_at TEXT,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        applied_seq INTEGER PRIMARY KEY AUTOINCREMENT,
        version INTEGER NOT NULL UNIQUE,
        applied_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_documents_user ON documents (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_document_chunks_doc ON document_chunks (document_id)",
    "CREATE INDEX IF NOT EXISTS ix_messages_conversation ON messages (conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_conversations_user ON conversations (user_id)",
)


def create_schema() -> list[str]:
    """Create the fixture tables, returning the statements that were applied."""
    from app.repositories.database.client import get_db

    applied: list[str] = []
    with get_db() as conn:
        for statement in SCHEMA_STATEMENTS:
            try:
                conn.execute(text(statement))
                applied.append(statement.strip().split("\n", 1)[0])
            except Exception as exc:  # noqa: BLE001 - reported, not fatal
                logger.warning("fixture.schema_skipped reason=%s", exc)
        try:
            conn.commit()
        except Exception:  # noqa: BLE001 - some session types autocommit
            pass
    return applied
