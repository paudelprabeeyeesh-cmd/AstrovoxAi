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


def _ensure_column(
    conn: sqlite3.Connection, table_name: str, column_name: str, definition: str
) -> None:
    existing = [
        row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    ]
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _ensure_index(
    conn: sqlite3.Connection, table: str, name: str, cols: str
) -> None:
    try:
        conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({cols})")
    except sqlite3.OperationalError:
        pass


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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            properties TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ab_events (
            id TEXT PRIMARY KEY,
            test_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            variant TEXT NOT NULL,
            event_name TEXT NOT NULL,
            event_value REAL,
            properties TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS funnels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            steps TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS funnel_events (
            id TEXT PRIMARY KEY,
            funnel_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            session_id TEXT,
            step_index INTEGER NOT NULL,
            step_name TEXT NOT NULL,
            entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            exited_at TIMESTAMP,
            completed INTEGER DEFAULT 0,
            drop_off_reason TEXT,
            properties TEXT
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cohorts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            definition TEXT NOT NULL,
            member_count INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cohort_members (
            id TEXT PRIMARY KEY,
            cohort_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            left_at TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cohort_metrics (
            id TEXT PRIMARY KEY,
            cohort_id TEXT NOT NULL,
            date TEXT NOT NULL,
            active_users INTEGER DEFAULT 0,
            new_retained INTEGER DEFAULT 0,
            returning_users INTEGER DEFAULT 0,
            churned_users INTEGER DEFAULT 0,
            retention_rate REAL DEFAULT 0,
            revenue REAL DEFAULT 0
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS retention_snapshots (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            cohort_date TEXT NOT NULL,
            day_0 INTEGER DEFAULT 1,
            day_1 INTEGER DEFAULT 0,
            day_3 INTEGER DEFAULT 0,
            day_7 INTEGER DEFAULT 0,
            day_14 INTEGER DEFAULT 0,
            day_30 INTEGER DEFAULT 0,
            day_60 INTEGER DEFAULT 0,
            day_90 INTEGER DEFAULT 0,
            last_active_date TEXT
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS revenue_events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            plan_name TEXT,
            plan_interval TEXT,
            payment_method TEXT,
            stripe_invoice_id TEXT,
            stripe_customer_id TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS custom_reports (
            id TEXT PRIMARY KEY,
            report_name TEXT NOT NULL,
            description TEXT,
            created_by TEXT NOT NULL,
            config TEXT NOT NULL,
            schedule TEXT,
            recipients TEXT DEFAULT '[]',
            last_run_at TIMESTAMP,
            is_public INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS help_articles (
            id TEXT PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            views INTEGER DEFAULT 0,
            helpful_count INTEGER DEFAULT 0,
            not_helpful_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tutorials (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            steps TEXT NOT NULL,
            difficulty TEXT DEFAULT 'beginner',
            estimated_time INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tutorial_progress (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            tutorial_id TEXT NOT NULL,
            current_step INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            UNIQUE(user_id, tutorial_id)
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            rating INTEGER,
            comment TEXT,
            page_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nps_surveys (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            score INTEGER NOT NULL,
            comment TEXT,
            survey_type TEXT DEFAULT 'periodic',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feature_requests (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            votes INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bug_reports (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'open',
            steps_to_reproduce TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_health (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            score REAL DEFAULT 0,
            factors TEXT DEFAULT '{}',
            last_calculated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_analytics (
            id TEXT PRIMARY KEY,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            period TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS status_page_incidents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'investigating',
            affected_services TEXT DEFAULT '[]',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_progress (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            current_step INTEGER DEFAULT 0,
            completed_steps TEXT DEFAULT '[]',
            completed INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS live_chat_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            agent_id TEXT,
            status TEXT DEFAULT 'open',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            sender_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id TEXT PRIMARY KEY,
            tenant_id TEXT,
            user_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'open',
            category TEXT DEFAULT 'general',
            assigned_to TEXT,
            tags TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ticket_comments (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            comment TEXT NOT NULL,
            is_internal INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS help_categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            parent_id TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_agents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT DEFAULT 'agent',
            team TEXT DEFAULT 'support',
            is_online INTEGER DEFAULT 0,
            max_tickets INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contextual_help (
            id TEXT PRIMARY KEY,
            page TEXT NOT NULL,
            element_selector TEXT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            trigger TEXT DEFAULT 'on_view',
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    conn.commit()
    _ensure_column(conn, "users", "last_login", "TEXT")
    _ensure_index(conn, "chats", "idx_chats_user_created", "user_id, created_at")
    _ensure_index(conn, "chats", "idx_chats_conversation", "conversation_id, created_at")
    _ensure_index(conn, "usage", "idx_usage_user_kind", "user_id, kind")
    _ensure_index(conn, "analytics_events", "idx_analytics_events_type", "event_type")
    _ensure_index(conn, "ab_events", "idx_ab_events_test", "test_id")
    _ensure_index(conn, "funnel_events", "idx_funnel_events_funnel", "funnel_id")
    _ensure_index(conn, "cohort_members", "idx_cohort_members_cohort", "cohort_id")
    _ensure_index(conn, "cohort_metrics", "idx_cohort_metrics_cohort_date", "cohort_id, date")
    _ensure_index(conn, "retention_snapshots", "idx_retention_user_cohort", "user_id, cohort_date")
    _ensure_index(conn, "revenue_events", "idx_revenue_user", "user_id")
    _ensure_index(conn, "revenue_events", "idx_revenue_type", "event_type")
    _ensure_index(conn, "custom_reports", "idx_custom_reports_owner", "created_by")
    _ensure_index(conn, "help_articles", "idx_help_articles_slug", "slug")
    _ensure_index(conn, "help_articles", "idx_help_articles_category", "category")
    _ensure_index(conn, "tutorials", "idx_tutorials_difficulty", "difficulty")
    _ensure_index(conn, "tutorial_progress", "idx_tutorial_progress_user", "user_id")
    _ensure_index(conn, "feedback", "idx_feedback_user", "user_id")
    _ensure_index(conn, "feedback", "idx_feedback_type", "type")
    _ensure_index(conn, "nps_surveys", "idx_nps_surveys_user", "user_id")
    _ensure_index(conn, "feature_requests", "idx_feature_requests_user", "user_id")
    _ensure_index(conn, "feature_requests", "idx_feature_requests_status", "status")
    _ensure_index(conn, "bug_reports", "idx_bug_reports_user", "user_id")
    _ensure_index(conn, "bug_reports", "idx_bug_reports_status", "status")
    _ensure_index(conn, "customer_health", "idx_customer_health_user", "user_id")
    _ensure_index(conn, "support_analytics", "idx_support_analytics_metric", "metric_name, period")
    _ensure_index(conn, "status_page_incidents", "idx_status_incidents_status", "status")
    _ensure_index(conn, "onboarding_progress", "idx_onboarding_user", "user_id")
    _ensure_index(conn, "live_chat_sessions", "idx_live_chat_user", "user_id")
    _ensure_index(conn, "live_chat_sessions", "idx_live_chat_status", "status")
    _ensure_index(conn, "chat_messages", "idx_chat_messages_session", "session_id")
    _ensure_index(conn, "support_tickets", "idx_support_tickets_user", "user_id")
    _ensure_index(conn, "support_tickets", "idx_support_tickets_status", "status")
    _ensure_index(conn, "support_tickets", "idx_support_tickets_assigned", "assigned_to")
    _ensure_index(conn, "ticket_comments", "idx_ticket_comments_ticket", "ticket_id")
    _ensure_index(conn, "help_categories", "idx_help_categories_parent", "parent_id")
    _ensure_index(conn, "support_agents", "idx_support_agents_team", "team")
    _ensure_index(conn, "contextual_help", "idx_contextual_help_page", "page")


def init_db() -> None:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    _ensure_tables(conn)
    conn.close()
    print(f"[db] Initialized SQLite DB at {DB_PATH}")


def get_db() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
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
        (
            username.strip(),
            email.strip().lower(),
            password_hash,
            datetime.utcnow().isoformat(),
        ),
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
        (identifier.strip(), identifier.strip().lower()),
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
        (datetime.utcnow().isoformat(), user_id),
    )
    conn.commit()
    conn.close()


def save_chat_message(
    conversation_id: str, user_id: str, role: str, message: str
) -> None:
    if not conversation_id or not user_id or not message:
        return
    conn = get_db()
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
    conn.commit()
    conn.close()


def get_conversation_history(conversation_id: str) -> List[Dict[str, str]]:
    conn = get_db()
    cur = conn.execute(
        "SELECT role, message, created_at FROM chats WHERE conversation_id=? ORDER BY created_at ASC",
        (conversation_id,),
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
        (user_id, today),
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
    cur.execute(
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
    conn.commit()
    conn.close()


def get_user_usage(user_id: str) -> Dict[str, int]:
    conn = get_db()
    cur = conn.execute(
        "SELECT COUNT(*) AS total_messages FROM chats WHERE user_id=?", (user_id,)
    )
    row = cur.fetchone()
    total = row["total_messages"] if row else 0
    conn.close()
    return {"total_messages": total}


def get_user_usage_summary(user_id: str) -> Dict[str, Any]:
    conn = get_db()
    rows = conn.execute(
        "SELECT kind, used, last_reset FROM usage WHERE user_id=?", (user_id,)
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
