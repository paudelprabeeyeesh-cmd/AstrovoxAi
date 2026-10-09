import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional


DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("ASTROVOX_DB_PATH", os.path.join(DB_DIR, "app.db"))


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
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
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
