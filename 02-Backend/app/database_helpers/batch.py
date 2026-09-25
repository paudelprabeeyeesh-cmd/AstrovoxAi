"""Batch upsert helpers for SQLAlchemy."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import insert, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql import table as TableClause

logger = logging.getLogger(__name__)


class BatchUpsert:
    """Perform bulk upserts into a table."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert(
        self,
        table_name: str,
        rows: list[dict[str, Any]],
        *,
        conflict_columns: list[str],
        update_columns: list[str] | None = None,
        return_defaults: bool = False,
    ) -> int:
        if not rows:
            return 0
        tbl = TableClause(table_name)
        stmt = insert(tbl)
        stmt = stmt.values(rows)
        update = update_columns or [c for c in rows[0].keys() if c not in conflict_columns]
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_={c: stmt.excluded[c] for c in update},
        )
        with self._engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
        return result.rowcount or 0
