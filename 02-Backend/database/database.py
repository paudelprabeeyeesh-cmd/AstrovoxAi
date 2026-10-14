import hashlib
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Generator, List, Optional, Tuple
from realtime import Any
from werkzeug.security import check_password_hash, generate_password_hash

from .connection import DB_PATH as _CONNECTION_DB_PATH, get_connection, transaction

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# One database location, owned by `database.connection`. This module used to
# read a differently-cased environment variable, so with both set the schema
# was created in one file while the queries ran against another, and every
# lookup failed with "no such table".
DB_PATH = os.getenv("Astravox_DB_PATH") or _CONNECTION_DB_PATH


def _ensure_db_dir() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)


def _column_name(row) -> str:
    """Read a column name from a `PRAGMA table_info` row.

    `PRAGMA table_info` returns (cid, name, type, notnull, dflt_value, pk),
    so the column name is the *second* positional element. `sqlite3.Row`
    subscripts by name, `database.connection.get_connection` installs a dict
    row factory, and a plain connection returns tuples. All three are used
    here, so the value is read by name when the row supports it and falls
    back to the positional index otherwise.
    """
    if isinstance(row, str):
        return row
    try:
        return str(row["name"])
    except (TypeError, IndexError, KeyError):
        pass
    try:
        return str(row[1])
    except (TypeError, IndexError, KeyError):
        return ""


def _ensure_column(
    conn: sqlite3.Connection, table_name: str, column_name: str, definition: str
) -> None:
    existing = [
        _column_name(row)
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
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
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            prompt TEXT,
            size TEXT DEFAULT '0x0',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}'
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS image_analyses (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            filename TEXT,
            question TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audio_outputs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            text TEXT DEFAULT '',
            voice TEXT DEFAULT '',
            output_path TEXT DEFAULT '',
            filename TEXT DEFAULT '',
            transcript TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS voice_profiles (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            profile_path TEXT NOT NULL,
            sample_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS speaker_profiles (
            id TEXT PRIMARY KEY,
            speaker_id TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            embedding_path TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            sample_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gpu_metrics (
            id TEXT PRIMARY KEY,
            device_id INTEGER NOT NULL,
            utilization_percent REAL NOT NULL,
            memory_used_mb REAL NOT NULL,
            memory_total_mb REAL NOT NULL,
            temperature_c REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory_metrics (
            id TEXT PRIMARY KEY,
            total_mb REAL NOT NULL,
            used_mb REAL NOT NULL,
            available_mb REAL NOT NULL,
            percent REAL NOT NULL,
            swap_used_mb REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_metrics (
            id TEXT PRIMARY KEY,
            endpoint TEXT NOT NULL,
            method TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            latency_ms REAL NOT NULL,
            user_id TEXT DEFAULT '',
            model TEXT DEFAULT '',
            provider TEXT DEFAULT '',
            tokens INTEGER DEFAULT 0,
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
    _ensure_index(conn, "audio_outputs", "idx_audio_outputs_user", "user_id")
    _ensure_index(conn, "audio_outputs", "idx_audio_outputs_type", "type")
    _ensure_index(conn, "voice_profiles", "idx_voice_profiles_user", "user_id")
    _ensure_index(conn, "speaker_profiles", "idx_speaker_profiles_user", "user_id")
    _ensure_index(conn, "speaker_profiles", "idx_speaker_profiles_speaker_id", "speaker_id")
    _ensure_index(conn, "gpu_metrics", "idx_gpu_metrics_device", "device_id, created_at")
    _ensure_index(conn, "memory_metrics", "idx_memory_metrics_created", "created_at")
    _ensure_index(conn, "api_metrics", "idx_api_metrics_endpoint", "endpoint, created_at")
    _ensure_index(conn, "api_metrics", "idx_api_metrics_status", "status_code")


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
    """Create the schema for the database at ``DB_PATH``.

    This file contained three concatenated copies of the module, so
    ``init_db``, ``get_db`` and ``create_user`` were each defined more than
    once and only the last definition was reachable. That reached copy was
    also the one that omitted the retrieval tables, so every document
    endpoint failed with "no such table".

    One definition survives, and it is the union of the useful work: the
    connection module owns the complete schema, this module's ``_ensure_tables``
    adds its analytics tables, ``_ensure_tables_rag`` adds the retrieval
    tables that used to be defined but never called, and the column
    migrations apply additively.
    """
    from .connection import init_db as _connection_init_db

    # The path is read at call time, not captured at import: the test suite
    # patches `database.database.DB_PATH` between calls, and a captured value
    # would keep pointing at the previous file. It is passed explicitly
    # because `connection.init_db` otherwise uses its own module-level
    # DB_PATH, resolved from a different environment variable, so the two
    # modules could otherwise create two databases.
    _connection_init_db(DB_PATH)

    conn = get_connection(DB_PATH)
    try:
        _ensure_tables(conn)
        _ensure_tables_rag(conn)

        # Additive column migrations. Because `get_connection` installs a
        # dict row factory, `_ensure_column` now reads column names by name
        # instead of by position.
        for table, column, definition in (
            ("conversations", "is_deleted", "INTEGER DEFAULT 0"),
            ("conversations", "last_message_at", "TEXT"),
            ("messages", "model_used", "TEXT"),
            ("messages", "tokens_used", "INTEGER"),
        ):
            if any(
                row.get("name") == table
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ):
                _ensure_column(conn, table, column, definition)

        conn.commit()
    finally:
        conn.close()


def get_db() -> sqlite3.Connection:
    """Return a connection to the configured database.

    The row factory is set here. `sqlite3.Row` supports subscripting by both
    name and position, which is what the callers in this module
    (``row["email"]``) and its tests expect; the dict factory installed by
    ``get_connection`` also supports names but not positions, so it is not
    substituted for it.
    """
    _ensure_db_dir()
    conn = get_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
def db_session() -> Generator[sqlite3.Connection, None, None]:
    """Yield a connection inside a transaction.

    This was a second ``get_db`` definition that shadowed the connection
    returning one above it, so every caller doing ``conn = get_db()`` then
    ``conn.execute(...)`` received a generator and raised AttributeError. It
    is renamed so both behaviours stay available under distinct names.
    """
    with _transaction() as conn:
        yield conn


def create_user(username: str, email: str, password: str) -> int:
    if not username or not email or not password:
        raise ValueError("Username, email, and password are required.")

    if get_user_by_username_or_email(username) or get_user_by_username_or_email(email):
        raise ValueError("Username or email already exists.")

    password_hash = generate_password_hash(password)
    with _transaction() as conn:
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
    with _transaction() as conn:
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


def _transaction():
    """Open a transaction on the *current* ``DB_PATH``.

    ``transaction(path)`` takes a path, but every caller in this module
    relies on the module-level ``DB_PATH`` being patchable (the test suite
    patches it between calls). Binding the captured global at call time would
    freeze the path at import, so it is resolved per use.
    """
    return transaction(globals().get("DB_PATH") or DB_PATH)


def update_user_last_login(user_id: int) -> None:
    if not user_id:
        return
    with _transaction() as conn:
        conn.execute(
            "UPDATE users SET last_login=? WHERE id=?",
            (datetime.utcnow().isoformat(), user_id),
        )


def save_chat_message(
    conversation_id: str, user_id: str, role: str, message: str
) -> None:
    if not conversation_id or not user_id or not message:
        return
    with _transaction() as conn:
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
    with _transaction() as conn:
        cur = conn.execute(
            "SELECT role, message, created_at FROM chats WHERE conversation_id=? ORDER BY created_at ASC",
            (conversation_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def check_limit(user_id: str, subscription: str, kind: str) -> Tuple[bool, int, int]:
    limits = {"free": 100, "pro": 1000}
    limit = limits.get(subscription, 100)
    with _transaction() as conn:
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
    with _transaction() as conn:
        today = datetime.utcnow().date().isoformat()
        cur = conn.execute(
            "SELECT id, used, last_reset FROM usage WHERE user_id=? AND kind=?",
            (user_id, kind),
        )
        row = cur.fetchone()
        if row:
            # Read by name: `get_connection` installs a dict row factory, so
            # positional unpacking raised on every row.
            record_id = row["id"]
            used = row["used"]
            last_reset = row["last_reset"]
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
    with _transaction() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) AS total_messages FROM chats WHERE user_id=?", (user_id,)
        )
        row = cur.fetchone()
        total = row["total_messages"] if row else 0
    return {"total_messages": total}


def get_user_usage_summary(user_id: str) -> Dict[str, Any]:
    with _transaction() as conn:
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
    with _transaction() as conn:
        row = conn.execute("SELECT COUNT(*) AS total_users FROM users").fetchone()
    return row["total_users"] if row else 0


def get_active_users() -> int:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS active_users FROM users WHERE last_login IS NOT NULL"
        ).fetchone()
    return row["active_users"] if row else 0


def get_total_messages() -> int:
    with _transaction() as conn:
        row = conn.execute("SELECT COUNT(*) AS total_messages FROM chats").fetchone()
    return row["total_messages"] if row else 0


def get_total_conversations() -> int:
    with _transaction() as conn:
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
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email=? LIMIT 1", (email.strip().lower(),)
        ).fetchone()
    return row


def create_user_with_password_hash(user_id: str, email: str, password_hash: str, role: str = "user", plan: str = "free") -> bool:
    """Insert a user given an already-hashed password.

    Renamed from ``create_user``: it shadowed the (username, email, password)
     version below, so ``create_user`` resolved to this incompatible
    signature and its columns (``role``/``plan``) that the authoritative
    ``users`` table does not have.
    """
    with _transaction() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, role, plan, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, email.strip().lower(), password_hash, role, plan, datetime.utcnow().isoformat()),
        )
    return True


def verify_user_credentials_by_id(user_id: str, password: str) -> bool:
    user = get_user_by_email(user_id) if "@" in user_id else None
    if user is None:
        with _transaction() as conn:
            user = conn.execute("SELECT * FROM users WHERE id=? LIMIT 1", (user_id,)).fetchone()
    if not user:
        return False
    return check_password_hash(user["password_hash"], password)


def create_email_verification_token(user_id: str, token: str, expires_at: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _transaction() as conn:
        conn.execute(
            "INSERT INTO email_verification_tokens (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, token_hash, expires_at),
        )
    return True


def verify_email_token(token: str) -> Optional[dict]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _transaction() as conn:
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
    with _transaction() as conn:
        conn.execute(
            "INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, token_hash, expires_at),
        )
    return True


def reset_password_with_token(token: str, new_password: str) -> Optional[str]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _transaction() as conn:
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
    with _transaction() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO mfa_secrets (id, user_id, secret) VALUES (?, ?, ?)",
            (str(uuid.uuid4()), user_id, secret),
        )
    return True


def get_mfa_secret(user_id: str) -> Optional[dict]:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM mfa_secrets WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def enable_mfa(user_id: str) -> bool:
    with _transaction() as conn:
        conn.execute("UPDATE mfa_secrets SET enabled=1 WHERE user_id=?", (user_id,))
    return True


def disable_mfa(user_id: str) -> bool:
    with _transaction() as conn:
        conn.execute("DELETE FROM mfa_secrets WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM mfa_backup_codes WHERE user_id=?", (user_id,))
    return True


def create_mfa_backup_codes(user_id: str, codes: List[str]) -> bool:
    with _transaction() as conn:
        for code in codes:
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            conn.execute(
                "INSERT INTO mfa_backup_codes (id, user_id, code_hash) VALUES (?, ?, ?)",
                (str(uuid.uuid4()), user_id, code_hash),
            )
    return True


def verify_mfa_backup_code(user_id: str, code: str) -> bool:
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    with _transaction() as conn:
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
    with _transaction() as conn:
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
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE session_token=? AND expires_at > ?",
            (session_token, datetime.utcnow().isoformat()),
        ).fetchone()
    return dict(row) if row else None


def get_session_by_refresh_token(refresh_token: str) -> Optional[dict]:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE refresh_token=? AND expires_at > ?",
            (refresh_token, datetime.utcnow().isoformat()),
        ).fetchone()
    return dict(row) if row else None


def delete_session(session_token: str) -> bool:
    with _transaction() as conn:
        cur = conn.execute("DELETE FROM user_sessions WHERE session_token=?", (session_token,))
    return cur.rowcount > 0


def delete_user_sessions(user_id: str) -> bool:
    with _transaction() as conn:
        conn.execute("DELETE FROM user_sessions WHERE user_id=?", (user_id,))
    return True


def create_device(user_id: str, name: str, fingerprint: str, device_type: str = "unknown", platform: str = None, browser: str = None) -> dict:
    device_id = str(uuid.uuid4())
    with _transaction() as conn:
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
    with _transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM devices WHERE user_id=? ORDER BY last_seen_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_device_by_fingerprint(fingerprint: str) -> Optional[dict]:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM devices WHERE fingerprint=?",
            (fingerprint,),
        ).fetchone()
    return dict(row) if row else None


def trust_device(device_id: str, user_id: str) -> bool:
    with _transaction() as conn:
        conn.execute(
            "UPDATE devices SET trusted=1 WHERE id=? AND user_id=?",
            (device_id, user_id),
        )
    return True


def delete_device(device_id: str, user_id: str) -> bool:
    with _transaction() as conn:
        cur = conn.execute(
            "DELETE FROM devices WHERE id=? AND user_id=?",
            (device_id, user_id),
        )
    return cur.rowcount > 0


def create_magic_link(user_id: str, email: str, token: str, expires_at: str) -> dict:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    link_id = str(uuid.uuid4())
    with _transaction() as conn:
        conn.execute(
            "INSERT INTO magic_links (id, user_id, email, token_hash, expires_at) VALUES (?, ?, ?, ?, ?)",
            (link_id, user_id, email, token_hash, expires_at),
        )
    return {"id": link_id, "email": email}


def verify_magic_link(token: str) -> Optional[dict]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _transaction() as conn:
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
    with _transaction() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO oauth_accounts (id, user_id, provider, provider_user_id, access_token, refresh_token, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (account_id, user_id, provider, provider_user_id, access_token, refresh_token, expires_at),
        )
    return {"id": account_id, "provider": provider}


def get_oauth_account(user_id: str, provider: str) -> Optional[dict]:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM oauth_accounts WHERE user_id=? AND provider=?",
            (user_id, provider),
        ).fetchone()
    return dict(row) if row else None


def get_oauth_account_by_provider_user_id(provider: str, provider_user_id: str) -> Optional[dict]:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM oauth_accounts WHERE provider=? AND provider_user_id=?",
            (provider, provider_user_id),
        ).fetchone()
    return dict(row) if row else None


def get_total_usage_records() -> int:
    with _transaction() as conn:
        row = conn.execute("SELECT SUM(used) AS total_usage FROM usage").fetchone()
    return row["total_usage"] if row and row["total_usage"] is not None else 0
