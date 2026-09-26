"""Database migration runner with idempotent file-based tracking."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


@dataclass
class MigrationRecord:
    name: str
    checksum: str
    applied_at: datetime


class MigrationRunner:
    """Run SQL migration files in order, tracking applied migrations."""

    def __init__(self, database_url: str, migrations_dir: str | Path) -> None:
        self._engine = create_engine(database_url)
        self._migrations_dir = Path(migrations_dir)
        self._ensure_tracking_table()

    def _ensure_tracking_table(self) -> None:
        with self._engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS schema_migrations ("
                    "  name VARCHAR(255) PRIMARY KEY,"
                    "  checksum VARCHAR(64) NOT NULL,"
                    "  applied_at TIMESTAMP NOT NULL DEFAULT now()"
                    ")"
                )
            )
            conn.commit()

    def _applied(self) -> dict[str, MigrationRecord]:
        with self._engine.connect() as conn:
            rows = conn.execute(text("SELECT name, checksum, applied_at FROM schema_migrations")).fetchall()
        return {row.name: MigrationRecord(row.name, row.checksum, row.applied_at) for row in rows}

    def pending(self) -> list[Path]:
        applied = self._applied()
        files = sorted(self._migrations_dir.glob("*.sql"))
        return [f for f in files if f.stem not in applied]

    def apply_file(self, path: Path) -> None:
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode()).hexdigest()
        applied = self._applied()
        if path.stem in applied and applied[path.stem].checksum == checksum:
            logger.debug("Migration %s already applied", path.name)
            return
        with self._engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        self._record(path.stem, checksum)
        logger.info("Applied migration %s", path.name)

    def apply_all(self) -> list[str]:
        pending = self.pending()
        if not pending:
            logger.info("No pending migrations")
            return []
        applied = []
        for path in pending:
            self.apply_file(path)
            applied.append(path.name)
        return applied

    def _record(self, name: str, checksum: str) -> None:
        with self._engine.connect() as conn:
            conn.execute(
                text("INSERT INTO schema_migrations (name, checksum) VALUES (:n, :c)"),
                {"n": name, "c": checksum},
            )
            conn.commit()

    def status(self) -> dict:
        applied = self._applied()
        files = sorted(self._migrations_dir.glob("*.sql"))
        return {
            "total": len(files),
            "applied": len(applied),
            "pending": len(files) - len(applied),
            "migrations": [
                {
                    "name": f.stem,
                    "status": "applied" if f.stem in applied else "pending",
                }
                for f in files
            ],
        }
