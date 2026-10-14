import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional


DB_DIR = os.path.dirname(os.path.abspath(__file__))

# Both spellings have appeared in the fleet: `database.database` read
# `Astravox_DB_PATH` while this module read `ASTROVOX_DB_PATH`. When both are
# set the two modules opened different files, so the schema was created in one
# and the queries ran against another. One canonical name, with the legacy
# spelling still honoured so a deployment that sets only that one keeps working.
DB_PATH = os.getenv("ASTROVOX_DB_PATH") or os.getenv(
    "Astravox_DB_PATH", os.path.join(DB_DIR, "app.db")
)


def _ensure_dir() -> None:
    os.makedirs(DB_DIR, exist_ok=True)


def _row_factory(cursor, row):
    return dict(zip([c[0] for c in cursor.description], row))


def get_connection(path: Optional[str] = None) -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = _row_factory
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path: Optional[str] = None) -> None:
    conn = get_connection(path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                last_reset TEXT
            );
            -- Kept for migration ordering: `version INTEGER PRIMARY KEY`
            -- is a rowid alias in SQLite, so rows are physically ordered by
            -- version and the order a migration actually ran in is
            -- unrecoverable. `applied_seq` is a real autoincrement, so
            -- `applied_versions()` can report application order.
            CREATE TABLE IF NOT EXISTS schema_migrations (
                applied_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL UNIQUE,
                applied_at TEXT NOT NULL
            );
            -- Auth service tables. `app/services/{device,magic_link,mfa,oauth,
            -- session}_service.py` read and write these, and no statement in the
            -- repo created them, so every one of those calls failed with
            -- "no such table" as soon as the modules were reachable.
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
            );
            CREATE TABLE IF NOT EXISTS magic_links (
                id TEXT PRIMARY KEY,
                email TEXT,
                token_hash TEXT,
                used INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS mfa_secrets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                secret TEXT,
                enabled INTEGER NOT NULL DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS mfa_backup_codes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                code_hash TEXT,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS oauth_accounts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                provider TEXT,
                provider_user_id TEXT,
                access_token TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_token TEXT,
                refresh_token TEXT,
                expires_at TEXT,
                last_activity_at TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                cost REAL NOT NULL,
                latency_ms INTEGER,
                rating INTEGER,
                correction TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS finetuning_jobs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                model TEXT NOT NULL,
                training_file TEXT NOT NULL,
                validation_file TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                fine_tuned_model TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                trained_tokens INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS training_datasets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size INTEGER NOT NULL,
                path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'uploaded',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS model_registry_entries (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                provider TEXT NOT NULL,
                model_id TEXT NOT NULL,
                stage TEXT NOT NULL DEFAULT 'development',
                metadata TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_finetuning_user ON finetuning_jobs(user_id);
            CREATE INDEX IF NOT EXISTS idx_training_datasets_user ON training_datasets(user_id);
            CREATE INDEX IF NOT EXISTS idx_model_registry_name ON model_registry_entries(name);
            CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key TEXT,
                value TEXT NOT NULL,
                embedding TEXT,
                memory_type TEXT,
                importance_score REAL DEFAULT 0.5,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ai_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
        """)
        conn.commit()
        try:
            from .enterprise_migrations import run_enterprise_migrations
            run_enterprise_migrations(conn)
        except Exception as _e:  # noqa: BLE001
            pass
    finally:
        conn.close()


@contextmanager
def transaction(path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(path)
    try:
        conn.execute("BEGIN")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
