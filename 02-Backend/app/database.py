import os
import time
import logging
from contextlib import contextmanager
from fastapi import HTTPException

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")

DB_PATH = os.getenv("ASTROVOX_DB", "astrovox.db")

_pool = None


def _create_pool():
    global _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required and must be a PostgreSQL connection string")
    if DATABASE_URL.startswith("sqlite"):
        _pool = None
        return
    import psycopg2
    from psycopg2.extras import RealDictCursor, register_vector

    class RealDictConnection(psycopg2.extensions.connection):
        def cursor(self, *args, **kwargs):
            return super().cursor(*args, cursor_factory=RealDictCursor, **kwargs)

    _pool = psycopg2.pool.ThreadedConnectionPool(
        2, 10,
        DATABASE_URL,
        pool_name="astrovox_pool",
        connection_factory=RealDictConnection,
    )


def _init_sqlite(conn):
    versions_dir = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")
    if not os.path.isdir(versions_dir):
        return
    skip = [
        "CREATE EXTENSION", "TYPE VECTOR", "JSONB", "USING IVFFLAT",
        "ALTER TABLE", "DROP COLUMN", "ADD COLUMN", "DROP TABLE", "DROP INDEX",
    ]
    for filename in sorted(os.listdir(versions_dir)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        filepath = os.path.join(versions_dir, filename)
        with open(filepath, "r") as f:
            content = f.read()
        i = 0
        while True:
            start = content.find('op.execute("""', i)
            if start == -1:
                break
            start += len('op.execute("""')
            end = content.find('"""', start)
            if end == -1:
                break
            sql = content[start:end].strip()
            sql_upper = sql.upper()
            if any(s in sql_upper for s in skip):
                i = end + 3
                continue
            try:
                conn.execute(sql)
            except Exception:
                pass
            i = end + 3


def _add_sqlite_column(conn, table, column, col_type):
    try:
        existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except Exception:
        pass


@contextmanager
def get_db():
    global _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required and must be a PostgreSQL connection string")
    if DATABASE_URL.startswith("sqlite"):
        import sqlite3
        db_path = DATABASE_URL.replace("sqlite:///", "")
        if not db_path:
            db_path = DB_PATH
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
        return
    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries):
        try:
            if _pool is None:
                _create_pool()
            conn = _pool.getconn()
        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("All database connection retries failed")
                raise HTTPException(status_code=503, detail="Service Unavailable: Database connection failed") from e
            continue

        try:
            register_vector(conn)
            yield conn
        finally:
            _pool.putconn(conn)
        return


def init_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required and must be a PostgreSQL connection string")
    if DATABASE_URL.startswith("sqlite"):
        import sqlite3
        db_path = DATABASE_URL.replace("sqlite:///", "")
        if not db_path:
            db_path = DB_PATH
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            _init_sqlite(conn)
            _add_sqlite_column(conn, "memories", "memory_type", "TEXT")
            _add_sqlite_column(conn, "memories", "importance_score", "REAL DEFAULT 0.5")
            _add_sqlite_column(conn, "users", "failed_payment_count", "INTEGER DEFAULT 0")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT,
                    metadata TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS tools (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    schema_json TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    message_id TEXT,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT,
                    result TEXT,
                    status TEXT DEFAULT 'pending',
                    error TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    steps INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    metadata TEXT,
                    created_at TEXT,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    instructions TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS project_files (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS agent_skills (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    version TEXT DEFAULT '1.0.0',
                    tools TEXT,
                    prompts TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    status TEXT DEFAULT 'queued',
                    input_data TEXT,
                    output_data TEXT,
                    error TEXT,
                    created_at TEXT,
                    completed_at TEXT
                );
            """)
            conn.commit()
        finally:
            conn.close()
        return
    with get_db() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
    _create_pool()
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
