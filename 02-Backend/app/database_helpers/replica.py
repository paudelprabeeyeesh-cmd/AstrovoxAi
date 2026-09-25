"""Read replica routing for SQLAlchemy."""

from __future__ import annotations

import logging
import random
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class ReplicaRouter:
    """Route read queries to replicas and writes to the primary."""

    def __init__(
        self,
        primary_url: str,
        replica_urls: list[str],
        *,
        pool_size: int = 5,
        max_overflow: int = 10,
        read_strategy: str = "random",
    ) -> None:
        self._primary = create_engine(primary_url, pool_size=pool_size, max_overflow=max_overflow)
        self._replicas = [create_engine(url, pool_size=pool_size, max_overflow=max_overflow) for url in replica_urls]
        self._read_strategy = read_strategy

    def primary(self) -> Engine:
        return self._primary

    def replica(self) -> Engine:
        if not self._replicas:
            return self._primary
        if self._read_strategy == "random":
            return random.choice(self._replicas)
        return self._replicas[0]

    def execute_read(self, query: str, params: dict | None = None) -> Any:
        engine = self.replica()
        with engine.connect() as conn:
            return conn.execute(text(query), params or {})

    def execute_write(self, query: str, params: dict | None = None) -> Any:
        engine = self.primary()
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            return result

    def health(self) -> dict:
        primary_ok = self._check(self._primary)
        replicas_ok = [self._check(r) for r in self._replicas]
        return {
            "primary": primary_ok,
            "replicas": replicas_ok,
            "total_replicas": len(self._replicas),
        }

    def _check(self, engine: Engine) -> bool:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
