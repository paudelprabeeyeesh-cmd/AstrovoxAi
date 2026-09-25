"""Seed data loader for loading initial/fixture data into the database."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.inspection import inspect

logger = logging.getLogger(__name__)


@dataclass
class SeedResult:
    table: str
    inserted: int
    skipped: int
    errors: list[str]


class SeedLoader:
    """Load seed data from JSON/YAML files into the database."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load_file(self, path: Path | str, *, truncate: bool = False) -> list[SeedResult]:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return self.load_dict(data, truncate=truncate)

    def load_dict(self, data: dict[str, list[dict[str, Any]]], *, truncate: bool = False) -> list[SeedResult]:
        results: list[SeedResult] = []
        with self._engine.connect() as conn:
            for table_name, rows in data.items():
                if not rows:
                    continue
                result = self._seed_table(conn, table_name, rows, truncate=truncate)
                results.append(result)
            conn.commit()
        return results

    def _seed_table(self, conn, table_name: str, rows: list[dict[str, Any]], *, truncate: bool) -> SeedResult:
        inserted = 0
        skipped = 0
        errors: list[str] = []
        try:
            inspector = inspect(self._engine)
            columns = [c["name"] for c in inspector.get_columns(table_name)]
            if truncate:
                conn.execute(text(f"DELETE FROM {table_name}"))
            for row in rows:
                try:
                    cols = [k for k in row.keys() if k in columns]
                    if not cols:
                        skipped += 1
                        continue
                    placeholders = ", ".join([f":{c}" for c in cols])
                    sql = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})"
                    conn.execute(text(sql), {c: row[c] for c in cols})
                    inserted += 1
                except Exception as exc:
                    skipped += 1
                    errors.append(f"{row}: {exc}")
        except Exception as exc:
            errors.append(str(exc))
        return SeedResult(table=table_name, inserted=inserted, skipped=skipped, errors=errors)
