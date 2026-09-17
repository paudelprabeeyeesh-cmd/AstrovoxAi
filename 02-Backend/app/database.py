import os
import time
import logging
from contextlib import contextmanager
from fastapi import HTTPException

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool = None


def _create_pool():
    global _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required and must be a PostgreSQL connection string")
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


@contextmanager
def get_db():
    global _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required and must be a PostgreSQL connection string")
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
    with get_db() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
    _create_pool()
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
