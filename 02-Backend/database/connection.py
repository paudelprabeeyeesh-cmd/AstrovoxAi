import os
import sqlite3
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
        """)
        conn.commit()
    finally:
        conn.close()
