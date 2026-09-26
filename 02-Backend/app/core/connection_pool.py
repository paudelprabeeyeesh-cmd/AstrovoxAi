"""SQLite connection pooling with thread-local cache and HTTP session pooling.

Uses a bounded pool of pre-opened connections per database path.
Reduces connection setup overhead on hot paths like chat message inserts.
Also provides a lightweight HTTP session pool for outbound API calls.
"""

import logging
import sqlite3
import threading
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPool:
    """Bounded pool of SQLite connections for a single database file."""

    db_path: str
    max_connections: int = 5
    _connections: list = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        import os
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        for _ in range(self.max_connections):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._connections.append(conn)

    def acquire(self) -> sqlite3.Connection:
        with self._lock:
            if self._connections:
                return self._connections.pop()
            return self._create_connection()

    def release(self, conn: sqlite3.Connection) -> None:
        with self._lock:
            if len(self._connections) < self.max_connections:
                self._connections.append(conn)
            else:
                conn.close()

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def close_all(self) -> None:
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()


_pools: dict[str, ConnectionPool] = {}
_pools_lock = threading.Lock()


def get_pool(db_path: str, max_connections: int = 5) -> ConnectionPool:
    with _pools_lock:
        if db_path not in _pools:
            _pools[db_path] = ConnectionPool(
                db_path=db_path, max_connections=max_connections
            )
        return _pools[db_path]


class PooledConnection:
    """Context manager for acquiring and releasing pooled connections."""

    def __init__(self, db_path: str, max_connections: int = 5):
        self.pool = get_pool(db_path, max_connections)
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        self.conn = self.pool.acquire()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                if exc_type:
                    self.conn.rollback()
                else:
                    self.conn.commit()
            except Exception:
                pass
            self.pool.release(self.conn)
        return False


try:
    import requests as _requests_lib

    _requests_available = True
except ImportError:
    _requests_available = False


class HTTPSessionPool:
    """Lightweight pool of reusable requests.Session objects."""

    def __init__(self, max_sessions: int = 10):
        self.max_sessions = max_sessions
        self._sessions: list = []
        self._lock = threading.Lock()
        self._created = 0

    def acquire(self):
        if not _requests_available:
            raise RuntimeError("requests is not installed")
        with self._lock:
            if self._sessions:
                return self._sessions.pop()
            if self._created < self.max_sessions:
                self._created += 1
                return _requests_lib.Session()
            return _requests_lib.Session()

    def release(self, session) -> None:
        with self._lock:
            if len(self._sessions) < self.max_sessions:
                self._sessions.append(session)
            else:
                session.close()

    def close_all(self) -> None:
        with self._lock:
            for session in self._sessions:
                try:
                    session.close()
                except Exception:
                    pass
            self._sessions.clear()
            self._created = 0


_http_pool: Optional[HTTPSessionPool] = None
_http_pool_lock = threading.Lock()


def get_http_pool(max_sessions: int = 10) -> HTTPSessionPool:
    global _http_pool
    if _http_pool is None:
        with _http_pool_lock:
            if _http_pool is None:
                _http_pool = HTTPSessionPool(max_sessions=max_sessions)
    return _http_pool
