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
            _add_sqlite_column(conn, "users", "role", "TEXT DEFAULT 'user'")
            _add_sqlite_column(conn, "users", "plan", "TEXT DEFAULT 'free'")
            _add_sqlite_column(conn, "knowledge_entities", "user_id", "TEXT")
            _add_sqlite_column(conn, "knowledge_entities", "properties", "TEXT")
            _add_sqlite_column(conn, "knowledge_relationships", "user_id", "TEXT")
            _add_sqlite_column(conn, "knowledge_relationships", "properties", "TEXT")
            _add_sqlite_column(conn, "templates", "description", "TEXT")
            _add_sqlite_column(conn, "templates", "content", "TEXT")
            _add_sqlite_column(conn, "workflows", "triggers", "TEXT")
            _add_sqlite_column(conn, "workflows", "enabled", "INTEGER DEFAULT 1")
            _add_sqlite_column(conn, "plugins", "install_count", "INTEGER DEFAULT 0")
            _add_sqlite_column(conn, "plugins", "rating", "REAL DEFAULT 0.0")
            _add_sqlite_column(conn, "plugins", "enabled", "INTEGER DEFAULT 0")
            _add_sqlite_column(conn, "plugins", "category", "TEXT")
            _add_sqlite_column(conn, "plugins", "publisher", "TEXT")
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
                CREATE TABLE IF NOT EXISTS voice_outputs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    text TEXT,
                    voice TEXT DEFAULT 'default',
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS voice_transcripts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    filename TEXT,
                    content TEXT,
                    transcript TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS images (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    prompt TEXT,
                    size TEXT DEFAULT '1024x1024',
                    url TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS image_analyses (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    filename TEXT,
                    question TEXT,
                    result TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS research_reports (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    query TEXT,
                    depth TEXT DEFAULT 'medium',
                    steps INTEGER DEFAULT 7,
                    status TEXT DEFAULT 'running',
                    result TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    artifact_type TEXT DEFAULT 'html',
                    created_at TEXT
                );
                 CREATE TABLE IF NOT EXISTS integration_tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    integration TEXT NOT NULL,
                    action TEXT,
                    target TEXT,
                    status TEXT DEFAULT 'running',
                    result TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS finetuning_jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    model TEXT,
                    training_file TEXT,
                    validation_file TEXT,
                    status TEXT DEFAULT 'queued',
                    created_at TEXT,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS mcp_servers (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    endpoint TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS knowledge_entities (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    entity_type TEXT,
                    name TEXT,
                    properties TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS knowledge_relationships (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    source_id TEXT,
                    target_id TEXT,
                    relationship_type TEXT,
                    properties TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS agent_orchestrations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    main_task TEXT,
                    num_agents INTEGER,
                    status TEXT DEFAULT 'starting',
                    created_at TEXT,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    id TEXT PRIMARY KEY,
                    orchestration_id TEXT,
                    name TEXT,
                    role TEXT,
                    status TEXT DEFAULT 'queued',
                    assigned_to TEXT,
                    result TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS plugins (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    price REAL DEFAULT 0,
                    config TEXT,
                    enabled INTEGER DEFAULT 0,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS plugin_installs (
                    plugin_id TEXT,
                    user_id TEXT,
                    installed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS conversation_branches (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    parent_id TEXT,
                    name TEXT,
                    context TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT,
                    steps TEXT,
                    triggers TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS api_requests (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    endpoint TEXT,
                    method TEXT,
                    status_code INTEGER,
                    response_time_ms REAL,
                    tokens_used INTEGER,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS speculative_decoding_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    prompt TEXT,
                    draft_model TEXT,
                    target_model TEXT,
                    num_draft_tokens INTEGER,
                    accepted_count INTEGER,
                    speedup_factor REAL,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS batch_decoding_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    batch_size INTEGER,
                    num_prompts INTEGER,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS tool_results (
                    id TEXT PRIMARY KEY,
                    tool_id TEXT,
                    arguments_json TEXT,
                    result TEXT,
                    execution_time_ms REAL,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS mcp_tools (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT,
                    description TEXT,
                    config TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    memory_type TEXT DEFAULT 'fact',
                    importance_score REAL DEFAULT 0.5
                );
                CREATE TABLE IF NOT EXISTS memory_incognito (
                    memory_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TEXT,
                    expires_at TEXT DEFAULT '2099-12-31T23:59:59Z'
                );
                CREATE TABLE IF NOT EXISTS rag_documents (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    title TEXT,
                    content TEXT,
                    chunks_count INTEGER,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT,
                    content TEXT,
                    chunk_index INTEGER,
                    embedding TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS model_versions (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    version TEXT,
                    provider TEXT,
                    architecture TEXT,
                    parameters TEXT,
                    snapshot_id TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS model_deployments (
                    id TEXT PRIMARY KEY,
                    model_id TEXT,
                    status TEXT,
                    deployed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS moe_runs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    num_experts INTEGER,
                    top_k INTEGER,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS moe_routing_logs (
                    id TEXT PRIMARY KEY,
                    run_id TEXT,
                    token_count INTEGER,
                    load_balance_loss REAL,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS distillation_jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    teacher_model TEXT,
                    student_model TEXT,
                    dataset_path TEXT,
                    alpha REAL,
                    beta REAL,
                    temperature REAL,
                    status TEXT,
                    created_at TEXT,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS quantization_logs (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    model TEXT,
                    bits INTEGER,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS plugins (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT,
                    description TEXT,
                    category TEXT,
                    price REAL DEFAULT 0,
                    config TEXT,
                    install_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    enabled INTEGER DEFAULT 0,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS plugin_installs (
                    plugin_id TEXT,
                    user_id TEXT,
                    installed_at TEXT
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
