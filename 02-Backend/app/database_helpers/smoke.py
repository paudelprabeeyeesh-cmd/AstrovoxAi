"""Smoke tests for verifying database restore integrity."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, inspect, text

logger = logging.getLogger(__name__)


@dataclass
class SmokeResult:
    passed: bool
    checks: list[dict[str, Any]]


class RestoreSmokeTest:
    """Run quick integrity checks after a database restore."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url)
        self._inspector = inspect(self._engine)

    def run(self, expected_tables: list[str], min_rows: dict[str, int] | None = None) -> SmokeResult:
        checks: list[dict[str, Any]] = []
        passed = True
        actual_tables = self._inspector.get_table_names()
        missing = [t for t in expected_tables if t not in actual_tables]
        if missing:
            passed = False
            checks.append({"name": "tables_exist", "passed": False, "detail": f"Missing tables: {missing}"})
        else:
            checks.append({"name": "tables_exist", "passed": True})
        for table in expected_tables:
            count = self._count_rows(table)
            expected = (min_rows or {}).get(table, 0)
            ok = count >= expected
            if not ok:
                passed = False
            checks.append({"name": f"row_count_{table}", "passed": ok, "actual": count, "expected_min": expected})
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks.append({"name": "query_execution", "passed": True})
        except Exception as exc:
            passed = False
            checks.append({"name": "query_execution", "passed": False, "detail": str(exc)})
        return SmokeResult(passed=passed, checks=checks)

    def _count_rows(self, table: str) -> int:
        with self._engine.connect() as conn:
            row = conn.execute(text(f"SELECT count(*) AS n FROM {table}")).fetchone()
        return row.n if row else 0
