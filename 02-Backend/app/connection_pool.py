import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import Generator, Optional

logger = logging.getLogger(__name__)


class SQLitePool:
    def __init__(self, db_path: str, size: int = 10) -> None:
        self.db_path = db_path
        self.size = size
        self._connections = []

    def get(self) -> sqlite3.Connection:
        if not self._connections:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        return self._connections.pop()

    def put(self, conn: sqlite3.Connection) -> None:
        if len(self._connections) < self.size:
            self._connections.append(conn)
        else:
            conn.close()


_pool: Optional[SQLitePool] = None


def get_pool(db_path: Optional[str] = None) -> SQLitePool:
    global _pool
    if _pool is None:
        _pool = SQLitePool(db_path or os.environ.get("ASTROVOX_DB_PATH", "app.db"))
    return _pool


@contextmanager
def pooled_connection(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    pool = get_pool(db_path)
    conn = pool.get()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.put(conn)
