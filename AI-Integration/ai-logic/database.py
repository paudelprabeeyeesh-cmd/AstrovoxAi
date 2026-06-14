"""
Astravox AI — database/database.py
Database connection, table creation, all DB helpers.
Created by: Dipson (Backend Engineer)
"""
import sqlite3
import datetime
import os

DATABASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "Astravox.db"
)
def init_db():
    print("💾 Database connection initialized successfully.")

def get_db():
    print("🗄️ Database session requested.")
    return None

def check_limit(user_usage):
    # Placeholder rate-limiting check
    return True

def increment_usage(user_usage):
    pass

def get_user_usage(user_id):
    return 0
    """Open and return a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()

    # USERS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER   PRIMARY KEY AUTOINCREMENT,
            username      TEXT      UNIQUE NOT NULL,
            email         TEXT      UNIQUE NOT NULL,
            password_hash TEXT      NOT NULL,
            full_name     TEXT      DEFAULT '',
            avatar_color  TEXT      DEFAULT '#7c6aff',
            role          TEXT      DEFAULT 'user',
            subscription  TEXT      DEFAULT 'free',
            ai_version    TEXT      DEFAULT 'Astravox-1.0',
            voice_pref    INTEGER   DEFAULT 0,
            is_active     INTEGER   DEFAULT 1,
            last_login    TIMESTAMP,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # CHATS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id          INTEGER   PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER   NOT NULL,
            role        TEXT      NOT NULL,
            message     TEXT      NOT NULL,
            subject     TEXT      DEFAULT 'general',
            ai_version  TEXT      DEFAULT 'Astravox-1.0',
            timestamp   TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # FILES TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id            INTEGER   PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER   NOT NULL,
            filename      TEXT      NOT NULL,
            original_name TEXT,
            file_type     TEXT,
            size_bytes    INTEGER   DEFAULT 0,
            drive_link    TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # DAILY USAGE TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_usage (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            usage_date     TEXT    NOT NULL,
            questions_used INTEGER DEFAULT 0,
            images_used    INTEGER DEFAULT 0,
            files_used     INTEGER DEFAULT 0,
            UNIQUE(user_id, usage_date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Astravox database ready — 4 tables initialized")


# ── USAGE FUNCTIONS ────────────────────────────────

def get_user_usage(user_id):
    """Get today's usage counts for a user."""
    conn  = get_db()
    today = datetime.date.today().isoformat()
    row   = conn.execute(
        "SELECT * FROM daily_usage WHERE user_id=? AND usage_date=?",
        (user_id, today)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"questions_used": 0, "images_used": 0, "files_used": 0}


def increment_usage(user_id, usage_type="questions"):
    """Add 1 to today's usage count."""
    allowed = {"questions", "images", "files"}
    if usage_type not in allowed:
        usage_type = "questions"
    conn  = get_db()
    today = datetime.date.today().isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO daily_usage (user_id, usage_date) VALUES (?,?)",
        (user_id, today)
    )
    col = f"{usage_type}_used"
    conn.execute(
        f"UPDATE daily_usage SET {col}={col}+1 WHERE user_id=? AND usage_date=?",
        (user_id, today)
    )
    conn.commit()
    conn.close()


def check_limit(user_id, subscription, usage_type="questions"):
    """
    Check if user can proceed.
    Returns: (can_proceed: bool, used: int, max_allowed: int)
    """
    limits = {
        "free":    {"questions": 20, "images": 1,  "files": 2},
        "basic":   {"questions": 50, "images": 3,  "files": 5},
        "premium": {"questions": 500,"images": 20, "files": 50},
    }
    plan        = limits.get(subscription, limits["free"])
    max_allowed = plan.get(usage_type, 20)
    usage       = get_user_usage(user_id)
    current     = usage.get(f"{usage_type}_used", 0)
    return current < max_allowed, current, max_allowed


# ── USER HELPERS ───────────────────────────────────

def get_user_by_id(user_id):
    conn = get_db()
    row  = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username):
    conn = get_db()
    row  = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_field(user_id, field, value):
    """Safely update one field for a user."""
    allowed_fields = {
        "full_name","avatar_color","ai_version","voice_pref",
        "subscription","last_login","is_active"
    }
    if field not in allowed_fields:
        return False
    conn = get_db()
    conn.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()
    return True