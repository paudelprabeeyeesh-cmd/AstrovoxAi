import os
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required and must be a PostgreSQL connection string")

_pool = None


def _create_pool():
    global _pool
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
    _create_pool()
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
