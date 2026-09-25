"""Connection pool health checks and monitoring."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)


@dataclass
class PoolHealth:
    status: str
    total_connections: int
    checkedin: int
    checkedout: int
    invalid: int
    overflow: int
    latency_ms: float
    checked_at: str


class PoolHealthCheck:
    """Monitor SQLAlchemy connection pool health."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._pool: Pool = engine.pool

    def check(self) -> PoolHealth:
        start = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000.0
        except Exception as exc:
            logger.error("Pool health check failed: %s", exc)
            latency = (time.perf_counter() - start) * 1000.0
            return PoolHealth(
                status="unhealthy",
                total_connections=self._safe_pool_int("size") + self._safe_pool_int("overflow"),
                checkedin=self._safe_pool_int("checkedin"),
                checkedout=self._safe_pool_int("checkedout"),
                invalid=self._safe_pool_int("invalid"),
                overflow=self._safe_pool_int("overflow"),
                latency_ms=latency,
                checked_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        status = "healthy"
        if latency > 500:
            status = "degraded"
        total = self._safe_pool_int("size") + self._safe_pool_int("overflow")
        if total > 0 and self._safe_pool_int("checkedout") / total > 0.9:
            status = "saturated"
        return PoolHealth(
            status=status,
            total_connections=total,
            checkedin=self._safe_pool_int("checkedin"),
            checkedout=self._safe_pool_int("checkedout"),
            invalid=self._safe_pool_int("invalid"),
            overflow=self._safe_pool_int("overflow"),
            latency_ms=latency,
            checked_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def _safe_pool_int(self, attr: str) -> int:
        return int(getattr(self._pool, attr, 0))

    def summary(self) -> dict:
        h = self.check()
        return {
            "status": h.status,
            "connections": {
                "total": h.total_connections,
                "checkedin": h.checkedin,
                "checkedout": h.checkedout,
                "invalid": h.invalid,
            },
            "latency_ms": round(h.latency_ms, 2),
            "checked_at": h.checked_at,
        }
