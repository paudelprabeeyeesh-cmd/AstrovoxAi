import os
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("DATABASE_URL must be set and must not be SQLite")


def _get_connection(db_url):
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(db_url)
        conn.cursor_factory = RealDictCursor
        return conn
    except ImportError:
        raise ImportError("psycopg2 is required for PostgreSQL")


@contextmanager
def get_db():
    conn = _get_connection(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")