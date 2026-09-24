import hashlib
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Generator, List, Optional, Tuple
from realtime import Any
from werkzeug.security import check_password_hash, generate_password_hash

from .connection import get_connection, transaction

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("Astravox_DB_PATH", os.path.join(BASE_DIR, "chat.db"))


def _ensure_db_dir() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)


def _ensure_column(
    conn: sqlite3.Connection, table_name: str, column_name: str, definition: str
) -> None:
    existing = [
        row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    ]
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _ensure_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            created_at TEXT,
            last_login TEXT
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            user_id TEXT,
            role TEXT,
            message TEXT,
            created_at TEXT
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            kind TEXT,
            used INTEGER,
            last_reset TEXT
        )
        """)
    conn.commit()
    _ensure_column(conn, "users", "last_login", "TEXT")
    _ensure_column(conn, "conversations", "is_deleted", "INTEGER DEFAULT 0")
    _ensure_column(conn, "conversations", "last_message_at", "TEXT")
    _ensure_column(conn, "messages", "model_used", "TEXT")
    _ensure_column(conn, "messages", "tokens_used", "INTEGER")
    _ensure_tables_rag(conn)


def _ensure_tables_rag(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_type TEXT NOT NULL,
            size INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
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
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_verification_user ON email_verification_tokens(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_verification_token ON email_verification_tokens(token_hash)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens(token_hash)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mfa_secrets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            secret TEXT NOT NULL,
            enabled INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mfa_secrets_user ON mfa_secrets(user_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mfa_backup_codes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mfa_backup_codes_user ON mfa_backup_codes(user_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            refresh_token TEXT NOT NULL UNIQUE,
            ip_address TEXT,
            user_agent TEXT,
            expires_at TEXT NOT NULL,
            last_activity_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh ON user_sessions(refresh_token)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            device_type TEXT DEFAULT 'unknown',
            platform TEXT,
            browser TEXT,
            fingerprint TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            trusted INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_fingerprint ON devices(fingerprint)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS magic_links (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            email TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            used INTEGER DEFAULT 0,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_magic_links_email ON magic_links(email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_magic_links_token ON magic_links(token_hash)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS oauth_accounts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            access_token TEXT,
            refresh_token TEXT,
            expires_at TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(provider, provider_user_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user ON oauth_accounts(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_oauth_accounts_provider ON oauth_accounts(provider, provider_user_id)")
    conn.commit()


def init_db() -> None:
    conn = get_connection(DB_PATH)
    _ensure_tables(conn)
    conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    with transaction(DB_PATH) as conn:
        yield conn


def create_user(username: str, email: str, password: str) -> int:
    if not username or not email or not password:
        raise ValueError("Username, email, and password are required.")

    if get_user_by_username_or_email(username) or get_user_by_username_or_email(email):
        raise ValueError("Username or email already exists.")

    password_hash = generate_password_hash(password)
    with transaction(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (
                username.strip(),
                email.strip().lower(),
                password_hash,
                datetime.utcnow().isoformat(),
            ),
        )
        return cur.lastrowid


def get_user_by_username_or_email(identifier: str) -> Optional[sqlite3.Row]:
    if not identifier:
        return None
    with transaction(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT * FROM users WHERE username=? OR email=? LIMIT 1",
            (identifier.strip(), identifier.strip().lower()),
        )
        return cur.fetchone()


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
    with transaction(DB_PATH) as conn:
        conn.execute(
            "UPDATE users SET last_login=? WHERE id=?",
            (datetime.utcnow().isoformat(), user_id),
        )


def save_chat_message(
    conversation_id: str, user_id: str, role: str, message: str
) -> None:
    if not conversation_id or not user_id or not message:
        return
    with transaction(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO chats (conversation_id, user_id, role, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                conversation_id,
                user_id,
                role,
                message.strip(),
                datetime.utcnow().isoformat(),
            ),
        )


def get_conversation_history(conversation_id: str) -> List[Dict[str, str]]:
    with transaction(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT role, message, created_at FROM chats WHERE conversation_id=? ORDER BY created_at ASC",
            (conversation_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def check_limit(user_id: str, subscription: str, kind: str) -> Tuple[bool, int, int]:
    limits = {"free": 100, "pro": 1000}
    limit = limits.get(subscription, 100)
    with transaction(DB_PATH) as conn:
        today = datetime.utcnow().date().isoformat()
        cur = conn.execute(
            "SELECT COUNT(*) AS c FROM chats WHERE user_id=? AND substr(created_at,1,10)=?",
            (user_id, today),
        )
        row = cur.fetchone()
        used = row["c"] if row else 0
    return (used < limit, used, limit)


def increment_usage(user_id: str, kind: str = "questions") -> None:
    if not user_id:
        return
    with transaction(DB_PATH) as conn:
        today = datetime.utcnow().date().isoformat()
        cur = conn.execute(
            "SELECT id, used, last_reset FROM usage WHERE user_id=? AND kind=?",
            (user_id, kind),
        )
        row = cur.fetchone()
        if row:
            record_id, used, last_reset = row
            if last_reset is None or last_reset.split("T")[0] != today:
                used = 0
            used += 1
            cur.execute(
                "UPDATE usage SET used=?, last_reset=? WHERE id=?",
                (used, datetime.utcnow().isoformat(), record_id),
            )
        else:
            cur.execute(
                "INSERT INTO usage (user_id, kind, used, last_reset) VALUES (?, ?, ?, ?)",
                (user_id, kind, 1, datetime.utcnow().isoformat()),
            )


def get_user_usage(user_id: str) -> Dict[str, int]:
    with transaction(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT COUNT(*) AS total_messages FROM chats WHERE user_id=?", (user_id,)
        )
        row = cur.fetchone()
        total = row["total_messages"] if row else 0
    return {"total_messages": total}


def get_user_usage_summary(user_id: str) -> Dict[str, Any]:
    with transaction(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT kind, used, last_reset FROM usage WHERE user_id=?", (user_id,)
        ).fetchall()
        summary = {row["kind"]: row["used"] for row in rows}
        last_reset = max([row["last_reset"] for row in rows], default=None)
    return {
        "summary": summary,
        "last_reset": last_reset,
    }


def get_total_users() -> int:
    with transaction(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) AS total_users FROM users").fetchone()
    return row["total_users"] if row else 0


def get_active_users() -> int:
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS active_users FROM users WHERE last_login IS NOT NULL"
        ).fetchone()
    return row["active_users"] if row else 0


def get_total_messages() -> int:
    with transaction(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) AS total_messages FROM chats").fetchone()
    return row["total_messages"] if row else 0


def get_total_conversations() -> int:
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(DISTINCT conversation_id) AS total_conversations FROM chats"
        ).fetchone()
    return row["total_conversations"] if row else 0


def get_site_metrics() -> Dict[str, int]:
    return {
        "total_users": get_total_users(),
        "active_users": get_active_users(),
        "total_messages": get_total_messages(),
        "total_conversations": get_total_conversations(),
        "total_usage_records": get_total_usage_records(),
    }


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email=? LIMIT 1", (email.strip().lower(),)
        ).fetchone()
    return row


def create_user(user_id: str, email: str, password_hash: str, role: str = "user", plan: str = "free") -> bool:
    with transaction(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, role, plan, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, email.strip().lower(), password_hash, role, plan, datetime.utcnow().isoformat()),
        )
    return True


def verify_user_credentials_by_id(user_id: str, password: str) -> bool:
    user = get_user_by_email(user_id) if "@" in user_id else None
    if user is None:
        with transaction(DB_PATH) as conn:
            user = conn.execute("SELECT * FROM users WHERE id=? LIMIT 1", (user_id,)).fetchone()
    if not user:
        return False
    return check_password_hash(user["password_hash"], password)


def create_email_verification_token(user_id: str, token: str, expires_at: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with transaction(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO email_verification_tokens (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, token_hash, expires_at),
        )
    return True


def verify_email_token(token: str) -> Optional[dict]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM email_verification_tokens WHERE token_hash=? AND used=0 AND expires_at > ?",
            (token_hash, datetime.utcnow().isoformat()),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE email_verification_tokens SET used=1 WHERE id=?",
                (row["id"],),
            )
            conn.execute("UPDATE users SET email_verified=1 WHERE id=?", (row["user_id"],))
    return dict(row) if row else None


def create_password_reset_token(user_id: str, token: str, expires_at: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with transaction(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, token_hash, expires_at),
        )
    return True


def reset_password_with_token(token: str, new_password: str) -> Optional[str]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM password_reset_tokens WHERE token_hash=? AND used=0 AND expires_at > ?",
            (token_hash, datetime.utcnow().isoformat()),
        ).fetchone()
        if row:
            password_hash = generate_password_hash(new_password)
            conn.execute(
                "UPDATE users SET password_hash=? WHERE id=?",
                (password_hash, row["user_id"]),
            )
            conn.execute(
                "UPDATE password_reset_tokens SET used=1 WHERE id=?",
                (row["id"],),
            )
            return row["user_id"]
    return None


def create_mfa_secret(user_id: str, secret: str) -> bool:
    with transaction(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO mfa_secrets (id, user_id, secret) VALUES (?, ?, ?)",
            (str(uuid.uuid4()), user_id, secret),
        )
    return True


def get_mfa_secret(user_id: str) -> Optional[dict]:
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM mfa_secrets WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def enable_mfa(user_id: str) -> bool:
    with transaction(DB_PATH) as conn:
        conn.execute("UPDATE mfa_secrets SET enabled=1 WHERE user_id=?", (user_id,))
    return True


def disable_mfa(user_id: str) -> bool:
    with transaction(DB_PATH) as conn:
        conn.execute("DELETE FROM mfa_secrets WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM mfa_backup_codes WHERE user_id=?", (user_id,))
    return True


def create_mfa_backup_codes(user_id: str, codes: List[str]) -> bool:
    with transaction(DB_PATH) as conn:
        for code in codes:
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            conn.execute(
                "INSERT INTO mfa_backup_codes (id, user_id, code_hash) VALUES (?, ?, ?)",
                (str(uuid.uuid4()), user_id, code_hash),
            )
    return True


def verify_mfa_backup_code(user_id: str, code: str) -> bool:
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM mfa_backup_codes WHERE user_id=? AND code_hash=? AND used=0",
            (user_id, code_hash),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE mfa_backup_codes SET used=1 WHERE id=?",
                (row["id"],),
            )
            return True
    return False


def create_session(user_id: str, session_token: str, refresh_token: str, ip_address: str = None, user_agent: str = None, expires_at: str = None) -> bool:
    with transaction(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO user_sessions (id, user_id, session_token, refresh_token, ip_address, user_agent, expires_at, last_activity_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                user_id,
                session_token,
                refresh_token,
                ip_address,
                user_agent,
                expires_at,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
            ),
        )
    return True


def get_session_by_token(session_token: str) -> Optional[dict]:
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE session_token=? AND expires_at > ?",
            (session_token, datetime.utcnow().isoformat()),
        ).fetchone()
    return dict(row) if row else None


def get_session_by_refresh_token(refresh_token: str) -> Optional[dict]:
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE refresh_token=? AND expires_at > ?",
            (refresh_token, datetime.utcnow().isoformat()),
        ).fetchone()
    return dict(row) if row else None


def delete_session(session_token: str) -> bool:
    with transaction(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM user_sessions WHERE session_token=?", (session_token,))
    return cur.rowcount > 0


def delete_user_sessions(user_id: str) -> bool:
    with transaction(DB_PATH) as conn:
        conn.execute("DELETE FROM user_sessions WHERE user_id=?", (user_id,))
    return True


def create_device(user_id: str, name: str, fingerprint: str, device_type: str = "unknown", platform: str = None, browser: str = None) -> dict:
    device_id = str(uuid.uuid4())
    with transaction(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO devices (id, user_id, name, device_type, platform, browser, fingerprint, last_seen_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                device_id,
                user_id,
                name,
                device_type,
                platform,
                browser,
                fingerprint,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
            ),
        )
    return {"id": device_id, "user_id": user_id, "name": name, "fingerprint": fingerprint}


def get_devices(user_id: str) -> List[dict]:
    with transaction(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT * FROM devices WHERE user_id=? ORDER BY last_seen_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_device_by_fingerprint(fingerprint: str) -> Optional[dict]:
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM devices WHERE fingerprint=?",
            (fingerprint,),
        ).fetchone()
    return dict(row) if row else None


def trust_device(device_id: str, user_id: str) -> bool:
    with transaction(DB_PATH) as conn:
        conn.execute(
            "UPDATE devices SET trusted=1 WHERE id=? AND user_id=?",
            (device_id, user_id),
        )
    return True


def delete_device(device_id: str, user_id: str) -> bool:
    with transaction(DB_PATH) as conn:
        cur = conn.execute(
            "DELETE FROM devices WHERE id=? AND user_id=?",
            (device_id, user_id),
        )
    return cur.rowcount > 0


def create_magic_link(user_id: str, email: str, token: str, expires_at: str) -> dict:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    link_id = str(uuid.uuid4())
    with transaction(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO magic_links (id, user_id, email, token_hash, expires_at) VALUES (?, ?, ?, ?, ?)",
            (link_id, user_id, email, token_hash, expires_at),
        )
    return {"id": link_id, "email": email}


def verify_magic_link(token: str) -> Optional[dict]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM magic_links WHERE token_hash=? AND used=0 AND expires_at > ?",
            (token_hash, datetime.utcnow().isoformat()),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE magic_links SET used=1 WHERE id=?",
                (row["id"],),
            )
    return dict(row) if row else None


def create_oauth_account(user_id: str, provider: str, provider_user_id: str, access_token: str = None, refresh_token: str = None, expires_at: str = None) -> dict:
    account_id = str(uuid.uuid4())
    with transaction(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO oauth_accounts (id, user_id, provider, provider_user_id, access_token, refresh_token, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (account_id, user_id, provider, provider_user_id, access_token, refresh_token, expires_at),
        )
    return {"id": account_id, "provider": provider}


def get_oauth_account(user_id: str, provider: str) -> Optional[dict]:
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM oauth_accounts WHERE user_id=? AND provider=?",
            (user_id, provider),
        ).fetchone()
    return dict(row) if row else None


def get_oauth_account_by_provider_user_id(provider: str, provider_user_id: str) -> Optional[dict]:
    with transaction(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM oauth_accounts WHERE provider=? AND provider_user_id=?",
            (provider, provider_user_id),
        ).fetchone()
    return dict(row) if row else None


def get_total_usage_records() -> int:
    with transaction(DB_PATH) as conn:
        row = conn.execute("SELECT SUM(used) AS total_usage FROM usage").fetchone()
    return row["total_usage"] if row and row["total_usage"] is not None else 0
