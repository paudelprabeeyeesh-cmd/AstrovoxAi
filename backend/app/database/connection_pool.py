import psycopg2
from psycopg2 import pool
from contextlib import contextmanager


class DatabasePool:
    def __init__(self, dsn: str, min_conn: int = 2, max_conn: int = 10):
        self._pool = pool.SimpleConnectionPool(min_conn, max_conn, dsn)

    @contextmanager
    def get_connection(self):
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def close(self):
        self._pool.closeall()
