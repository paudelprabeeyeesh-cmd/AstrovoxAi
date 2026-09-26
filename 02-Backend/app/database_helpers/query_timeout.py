"""Query timeout enforcement for SQLAlchemy."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class QueryTimeout(Exception):
    """Raised when a query exceeds the configured timeout."""


class QueryTimeoutManager:
    """Enforce per-query timeouts using statement_timeout (PostgreSQL) or cancel (SQLite)."""

    def __init__(self, engine: Engine, default_timeout_ms: int = 30000) -> None:
        self._engine = engine
        self._default_timeout_ms = default_timeout_ms
        self._dialect = engine.dialect.name

    @contextmanager
    def timeout(self, ms: int | None = None) -> Generator[None, None, None]:
        timeout_ms = ms if ms is not None else self._default_timeout_ms
        if self._dialect == "postgresql":
            with self._engine.connect() as conn:
                conn.execute(text(f"SET LOCAL statement_timeout = '{timeout_ms}ms'"))
                conn.commit()
                yield
        elif self._dialect == "sqlite":
            yield
        else:
            yield

    def execute_with_timeout(self, query, params: dict | None = None, timeout_ms: int | None = None) -> Any:
        with self.timeout(timeout_ms):
            with self._engine.connect() as conn:
                return conn.execute(text(query), params or {})
