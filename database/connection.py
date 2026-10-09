import contextlib
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB", "astrovox")
    user: str = os.getenv("POSTGRES_USER", "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "")
    min_connections: int = int(os.getenv("DB_POOL_MIN", "2"))
    max_connections: int = int(os.getenv("DB_POOL_MAX", "20"))
    timeout: float = float(os.getenv("DB_POOL_TIMEOUT", "30"))


class DatabasePool:
    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        self.config = config or DatabaseConfig()
        self._pool: List[Any] = []
        self._in_use: Dict[Any, bool] = {}
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            for _ in range(self.config.min_connections):
                conn = self._create_connection()
                if conn:
                    self._pool.append(conn)
            self._initialized = True
            logger.info(
                "Database pool initialized with %d connections",
                len(self._pool),
            )

    def _create_connection(self) -> Any:
        try:
            import psycopg2
            return psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                connect_timeout=self.config.timeout,
            )
        except Exception as exc:
            logger.error("Failed to create database connection: %s", exc)
            return None

    def acquire(self) -> Any:
        if not self._initialized:
            self.initialize()
        with self._lock:
            if self._pool:
                conn = self._pool.pop()
                self._in_use[conn] = True
                return conn
            if len(self._in_use) < self.config.max_connections:
                conn = self._create_connection()
                if conn:
                    self._in_use[conn] = True
                    return conn
            raise RuntimeError("Database connection pool exhausted")

    def release(self, conn: Any) -> None:
        with self._lock:
            self._in_use.pop(conn, None)
            if len(self._pool) < self.config.max_connections and conn and not conn.closed:
                self._pool.append(conn)
            else:
                with contextlib.suppress(Exception):
                    conn.close()

    def health_check(self) -> bool:
        try:
            conn = self.acquire()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return True
            finally:
                self.release(conn)
        except Exception as exc:
            logger.error("Database health check failed: %s", exc)
            return False

    def close_all(self) -> None:
        with self._lock:
            for conn in list(self._pool) + list(self._in_use.keys()):
                with contextlib.suppress(Exception):
                    if not conn.closed:
                        conn.close()
            self._pool.clear()
            self._in_use.clear()
            self._initialized = False


_pool: Optional[DatabasePool] = None
_pool_lock = threading.Lock()


def get_pool() -> DatabasePool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = DatabasePool()
    return _pool


@contextlib.contextmanager
def get_connection() -> Generator[Any, None, None]:
    pool = get_pool()
    conn = pool.acquire()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.release(conn)


def init_db() -> None:
    get_pool().initialize()


def close_db() -> None:
    global _pool
    if _pool:
        _pool.close_all()
        _pool = None
