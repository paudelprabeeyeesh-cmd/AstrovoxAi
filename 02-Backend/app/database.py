import os
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("DATABASE_URL must be set and must not be SQLite")

_pool = None


def _create_pool():
    global _pool
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        class RealDictConnection(psycopg2.extensions.connection):
            def cursor(self, *args, **kwargs):
                return super().cursor(*args, cursor_factory=RealDictCursor, **kwargs)
        
        _pool = psycopg2.pool.ThreadedConnectionPool(
            2, 10,
            DATABASE_URL,
            pool_name="astrovox_pool",
            connection_factory=RealDictConnection,
        )
    except ImportError:
        raise ImportError("psycopg2 is required for PostgreSQL")
    except Exception as e:
        raise RuntimeError(f"Failed to create connection pool: {e}")


@contextmanager
def get_db():
    if _pool is None:
        _create_pool()
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)


def init_db():
    from alembic.config import Config
    from alembic import command
    _create_pool()
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")