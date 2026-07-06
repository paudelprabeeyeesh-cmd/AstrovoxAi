import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from realtime import Any
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("Astravox_DB_PATH", os.path.join(BASE_DIR, "chat.db"))


def _ensure_db_dir() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _ensure_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            created_at TEXT,
            last_login TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            user_id TEXT,
            role TEXT,
            message TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            kind TEXT,
            used INTEGER,
            last_reset TEXT
        )
        """
    )
    conn.commit()
    _ensure_column(conn, "users", "last_login", "TEXT")


def init_db() -> None:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    conn.close()
    print(f"[db] Initialized SQLite DB at {DB_PATH}")


def get_db() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    return conn


def create_user(username: str, email: str, password: str) -> int:
    if not username or not email or not password:
        raise ValueError("Username, email, and password are required.")

    if get_user_by_username_or_email(username) or get_user_by_username_or_email(email):
        raise ValueError("Username or email already exists.")

    password_hash = generate_password_hash(password)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (username.strip(), email.strip().lower(), password_hash, datetime.utcnow().isoformat())
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_username_or_email(identifier: str) -> Optional[sqlite3.Row]:
    if not identifier:
        return None
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM users WHERE username=? OR email=? LIMIT 1",
        (identifier.strip(), identifier.strip().lower())
    )
    row = cur.fetchone()
    conn.close()
    return row


def verify_user_credentials(identifier: str, password: str) -> Optional[sqlite3.Row]:
    user = get_user_by_username_or_email(identifier)
    if not user:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def update_user_last_login(user_id: int) -> None:
    if not user_id:
        return
    conn = get_db()
    conn.execute(
        "UPDATE users SET last_login=? WHERE id=?",
        (datetime.utcnow().isoformat(), user_id)
    )
    conn.commit()
    conn.close()


def save_chat_message(conversation_id: str, user_id: str, role: str, message: str) -> None:
    if not conversation_id or not user_id or not message:
        return
    conn = get_db()
    conn.execute(
        "INSERT INTO chats (conversation_id, user_id, role, message, created_at) VALUES (?, ?, ?, ?, ?)",
        (conversation_id, user_id, role, message.strip(), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_conversation_history(conversation_id: str) -> List[Dict[str, str]]:
    conn = get_db()
    cur = conn.execute(
        "SELECT role, message, created_at FROM chats WHERE conversation_id=? ORDER BY created_at ASC",
        (conversation_id,)
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def check_limit(user_id: str, subscription: str, kind: str) -> Tuple[bool, int, int]:
    limits = {"free": 100, "pro": 1000}
    limit = limits.get(subscription, 100)
    conn = get_db()
    today = datetime.utcnow().date().isoformat()
    cur = conn.execute(
        "SELECT COUNT(*) AS c FROM chats WHERE user_id=? AND substr(created_at,1,10)=?",
        (user_id, today)
    )
    row = cur.fetchone()
    used = row["c"] if row else 0
    conn.close()
    return (used < limit, used, limit)


def increment_usage(user_id: str, kind: str = "questions") -> None:
    if not user_id:
        return
    conn = get_db()
    cur = conn.cursor()
    today = datetime.utcnow().date().isoformat()
    cur.execute("SELECT id, used, last_reset FROM usage WHERE user_id=? AND kind=?", (user_id, kind))
    row = cur.fetchone()
    if row:
        record_id, used, last_reset = row
        if last_reset is None or last_reset.split('T')[0] != today:
            used = 0
        used += 1
        cur.execute(
            "UPDATE usage SET used=?, last_reset=? WHERE id=?",
            (used, datetime.utcnow().isoformat(), record_id)
        )
    else:
        cur.execute(
            "INSERT INTO usage (user_id, kind, used, last_reset) VALUES (?, ?, ?, ?)",
            (user_id, kind, 1, datetime.utcnow().isoformat())
        )
    conn.commit()
    conn.close()


def get_user_usage(user_id: str) -> Dict[str, int]:
    conn = get_db()
    cur = conn.execute(
        "SELECT COUNT(*) AS total_messages FROM chats WHERE user_id=?",
        (user_id,)
    )
    row = cur.fetchone()
    total = row["total_messages"] if row else 0
    conn.close()
    return {"total_messages": total}


def get_user_usage_summary(user_id: str) -> Dict[str, Any]:
    conn = get_db()
    rows = conn.execute(
        "SELECT kind, used, last_reset FROM usage WHERE user_id=?",
        (user_id,)
    ).fetchall()
    conn.close()
    summary = {row["kind"]: row["used"] for row in rows}
    last_reset = max([row["last_reset"] for row in rows], default=None)
    return {
        "summary": summary,
        "last_reset": last_reset,
    }


def get_total_users() -> int:
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) AS total_users FROM users").fetchone()
    conn.close()
    return row["total_users"] if row else 0


def get_active_users() -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS active_users FROM users WHERE last_login IS NOT NULL"
    ).fetchone()
    conn.close()
    return row["active_users"] if row else 0


def get_total_messages() -> int:
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) AS total_messages FROM chats").fetchone()
    conn.close()
    return row["total_messages"] if row else 0


def get_total_conversations() -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(DISTINCT conversation_id) AS total_conversations FROM chats"
    ).fetchone()
    conn.close()
    return row["total_conversations"] if row else 0


def get_site_metrics() -> Dict[str, int]:
    return {
        "total_users": get_total_users(),
        "active_users": get_active_users(),
        "total_messages": get_total_messages(),
        "total_conversations": get_total_conversations(),
        "total_usage_records": get_total_usage_records(),
    }


def get_total_usage_records() -> int:
    conn = get_db()
    row = conn.execute("SELECT SUM(used) AS total_usage FROM usage").fetchone()
    conn.close()
    return row["total_usage"] if row and row["total_usage"] is not None else 0
