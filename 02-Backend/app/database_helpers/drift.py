"""Schema drift detector: compare live database schema with SQLAlchemy models."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


@dataclass
class ColumnDiff:
    table: str
    column: str
    issue: str


@dataclass
class DriftReport:
    is_clean: bool
    missing_tables: list[str] = field(default_factory=list)
    extra_tables: list[str] = field(default_factory=list)
    column_diffs: list[ColumnDiff] = field(default_factory=list)


class SchemaDriftDetector:
    """Detect drift between SQLAlchemy models and the live database schema."""

    def __init__(self, engine: Any, base: type[DeclarativeBase]) -> None:
        self._engine = engine
        self._inspector = inspect(engine)
        self._base = base

    def detect(self) -> DriftReport:
        model_tables = {t.name for t in self._base.metadata.tables.values()}
        live_tables = set(self._inspector.get_table_names())
        missing = sorted(model_tables - live_tables)
        extra = sorted(live_tables - model_tables)
        diffs = self._diff_columns(model_tables)
        return DriftReport(
            is_clean=not missing and not extra and not diffs,
            missing_tables=missing,
            extra_tables=extra,
            column_diffs=diffs,
        )

    def _diff_columns(self, model_tables: set[str]) -> list[ColumnDiff]:
        diffs: list[ColumnDiff] = []
        for table_name in model_tables:
            try:
                live_cols = {c["name"]: c for c in self._inspector.get_columns(table_name)}
            except NoSuchTableError:
                diffs.append(ColumnDiff(table=table_name, column="*", issue="table_missing_in_db"))
                continue
            model_cols = {c.name: c for c in self._base.metadata.tables[table_name].columns}
            for name, col in model_cols.items():
                live = live_cols.get(name)
                if live is None:
                    diffs.append(ColumnDiff(table=table_name, column=name, issue="missing_in_db"))
                    continue
                if str(col.type) != str(live.get("type")):
                    diffs.append(ColumnDiff(table=table_name, column=name, issue=f"type_mismatch: model={col.type} db={live.get('type')}"))
            for name in live_cols:
                if name not in model_cols:
                    diffs.append(ColumnDiff(table=table_name, column=name, issue="extra_in_db"))
        return diffs
