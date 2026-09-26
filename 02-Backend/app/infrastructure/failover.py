"""Enhanced database connection pooling with automatic failover."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    FAILED = "failed"
    DISPOSED = "disposed"
    TESTING = "testing"


@dataclass
class ConnectionConfig:
    url: str
    pool_min_size: int = 5
    pool_max_size: int = 20
    pool_overflow: int = 10
    pool_recycle: int = 3600
    pool_timeout: int = 30
    pool_pre_ping: bool = True
    connect_timeout: int = 10
    command_timeout: int = 30
    failover_enabled: bool = True
    failover_urls: List[str] = field(default_factory=list)


@dataclass
class PooledConnection:
    connection_id: str
    state: ConnectionState = ConnectionState.IDLE
    url: str = ""
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    error_count: int = 0


class EnhancedConnectionPool:
    """Database connection pool with automatic failover."""

    def __init__(self, config: ConnectionConfig) -> None:
        self._config = config
        self._connections: List[PooledConnection] = []
        self._primary_url = config.url
        self._failover_urls = config.failover_urls
        self._active_index = 0
        self._lock = asyncio.Lock()
        self._health_check_interval = 60
        self._recycle_interval = config.pool_recycle
        self._initialized = asyncio.Event()

    async def initialize(self) -> None:
        async with self._lock:
            for _ in range(self._config.pool_min_size):
                conn = await self._create_connection(self._primary_url)
                self._connections.append(conn)
        self._initialized.set()
        asyncio.create_task(self._background_health_loop())

    async def acquire(self) -> PooledConnection:
        await self._initialized.wait()
        async with self._lock:
            for conn in self._connections:
                if conn.state == ConnectionState.IDLE:
                    conn.state = ConnectionState.ACTIVE
                    conn.last_used = time.time()
                    conn.use_count += 1
                    return conn
            if len(self._connections) < self._config.pool_max_size:
                conn = await self._create_connection(self._get_current_url())
                self._connections.append(conn)
                return conn
            raise TimeoutError("No database connections available")

    async def release(self, conn: PooledConnection) -> None:
        async with self._lock:
            if conn.state == ConnectionState.FAILED:
                await self._replace_connection(conn)
            else:
                conn.state = ConnectionState.IDLE
                conn.last_used = time.time()

    async def _create_connection(self, url: str) -> PooledConnection:
        import uuid
        conn = PooledConnection(connection_id=str(uuid.uuid4())[:8], url=url)
        if self._config.failover_enabled:
            ok = await self._test_connection(conn)
            if not ok:
                conn.state = ConnectionState.FAILED
                conn.error_count += 1
                logger.warning("Failed to create connection for %s", url)
                return conn
        conn.state = ConnectionState.IDLE
        return conn

    async def _test_connection(self, conn: PooledConnection) -> bool:
        if not conn.url:
            return False
        try:
            await asyncio.wait_for(
                self._ping(conn.url), timeout=self._config.connect_timeout
            )
            return True
        except Exception:
            return False

    async def _ping(self, url: str) -> None:
        from sqlalchemy import create_engine, text
        engine = create_engine(url, pool_size=1)
        with engine.connect() as session:
            session.execute(text("SELECT 1"))

    async def _replace_connection(self, conn: PooledConnection) -> None:
        for i, c in enumerate(self._connections):
            if c.connection_id == conn.connection_id:
                self._connections.remove(c)
                new_conn = await self._create_connection(self._get_current_url())
                self._connections.insert(i, new_conn)
                return

    async def _background_health_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._run_health_checks()
            except Exception as exc:
                logger.error("Health check loop error: %s", exc)

    async def _run_health_checks(self) -> None:
        async with self._lock:
            for conn in self._connections:
                if conn.state == ConnectionState.ACTIVE:
                    continue
                if time.time() - conn.last_used > self._recycle_interval:
                    await self._replace_connection(conn)
                    continue
                ok = await self._test_connection(conn)
                if not ok:
                    logger.warning("Health check failed for %s", conn.connection_id)
                    if conn.url != self._primary_url:
                        await self._replace_connection(conn)
                        continue
                if not ok and self._failover_urls:
                    next_idx = min(conn.error_count, len(self._failover_urls) - 1)
                    self._active_index = (self._active_index + 1) % max(1, len(self._failover_urls))
                    await self._replace_connection(conn)

    def _get_current_url(self) -> str:
        if self._failover_urls:
            return self._failover_urls[self._active_index % len(self._failover_urls)]
        return self._primary_url

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._connections),
            "active": sum(1 for c in self._connections if c.state == ConnectionState.ACTIVE),
            "idle": sum(1 for c in self._connections if c.state == ConnectionState.IDLE),
            "failed": sum(1 for c in self._connections if c.state == ConnectionState.FAILED),
            "pool_max_size": self._config.pool_max_size,
            "current_url": self._get_current_url(),
        }


class FailoverManager:
    """Manage database failover and circuit breaking."""

    def __init__(self) -> None:
        self._state = "closed"
        self._failure_count = 0
        self._failure_threshold = 5
        self._recovery_timeout = 60
        self._last_failure_time = 0.0
        self._lock = asyncio.Lock()

    async def get_state(self) -> str:
        async with self._lock:
            if self._state == "open":
                if time.time() - self._last_failure_time > self._recovery_timeout:
                    self._state = "half-open"
            return self._state

    async def record_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._state = "open"
                logger.warning("Circuit breaker opened after %d failures", self._failure_count)

    async def record_success(self) -> None:
        async with self._lock:
            self._failure_count = 0
            self._state = "closed"

    def is_available(self) -> bool:
        return self._state in ("closed", "half-open")


_failover_manager: Optional[FailoverManager] = None


def get_failover_manager() -> FailoverManager:
    global _failover_manager
    if _failover_manager is None:
        _failover_manager = FailoverManager()
    return _failover_manager
