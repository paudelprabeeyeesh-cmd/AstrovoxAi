"""JSON path query helpers for PostgreSQL JSONB."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class JsonPathResult:
    path: str
    value: Any
    found: bool


class JsonQuery:
    """Query and extract values from JSONB columns using JSON path expressions."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self, table: str, column: str, id: Any, path: str) -> Any:
        sql = f"SELECT {column} #> :path AS value FROM {table} WHERE id = :id"
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"path": self._to_pg_path(path), "id": id}).fetchone()
        return row.value if row else None

    def get_text(self, table: str, column: str, id: Any, path: str) -> str | None:
        val = self.get(table, column, id, path)
        if val is None:
            return None
        if isinstance(val, str):
            return val
        return str(val)

    def exists(self, table: str, column: str, id: Any, path: str) -> bool:
        sql = f"SELECT EXISTS(SELECT 1 FROM {table} WHERE id = :id AND {column} #> :path IS NOT NULL) AS found"
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"path": self._to_pg_path(path), "id": id}).fetchone()
        return bool(row.found) if row else False

    def contains(self, table: str, column: str, id: Any, key: str, value: Any) -> bool:
        sql = f"SELECT EXISTS(SELECT 1 FROM {table} WHERE id = :id AND {column} @> :obj) AS found"
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"id": id, "obj": {key: value}}).fetchone()
        return bool(row.found) if row else False

    def contains_any(self, table: str, column: str, id: Any, candidates: list[str]) -> list[str]:
        placeholders = ", ".join([f":c{i}" for i in range(len(candidates))])
        params = {f"c{i}": c for i, c in enumerate(candidates)}
        params["id"] = id
        sql = f"""
            SELECT jsonb_path_query_array({column}, '$.* ? (@ like_regex $pattern)') AS matches
            FROM {table} WHERE id = :id
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).fetchone()
        return list(row.matches) if row and row.matches else []

    def _to_pg_path(self, path: str) -> list[str]:
        return [p for p in path.split(".") if p]
