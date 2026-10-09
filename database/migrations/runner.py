import importlib.util
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MigrationRecord:
    version: str
    name: str
    applied_at: str

    @classmethod
    def from_row(cls, row: tuple) -> "MigrationRecord":
        return cls(version=row[0], name=row[1], applied_at=row[2])


class MigrationRunner:
    def __init__(self, migrations_dir: Optional[Path] = None) -> None:
        self.migrations_dir = migrations_dir or Path(__file__).parent
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        from database.connection import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                    )
                    """
                )
                conn.commit()

    def _get_applied_migrations(self) -> List[MigrationRecord]:
        from database.connection import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version, name, applied_at FROM schema_migrations ORDER BY version")
                return [MigrationRecord.from_row(row) for row in cur.fetchall()]

    def _get_pending_migrations(self, applied: List[MigrationRecord]) -> List[Path]:
        applied_versions = {m.version for m in applied}
        pending = []
        for path in sorted(self.migrations_dir.glob("*.sql")):
            version = path.stem.split("_")[0]
            if version not in applied_versions:
                pending.append(path)
        return pending

    def run_pending(self) -> List[str]:
        applied = self._get_applied_migrations()
        pending = self._get_pending_migrations(applied)
        if not pending:
            logger.info("No pending migrations")
            return []

        applied_now = []
        for path in pending:
            version = path.stem.split("_")[0]
            logger.info("Applying migration %s", path.name)
            sql = path.read_text(encoding="utf-8")
            from database.connection import get_connection
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                        (version, path.name),
                    )
                conn.commit()
            applied_now.append(path.name)
            logger.info("Migration %s applied", path.name)
        return applied_now

    def get_status(self) -> Dict[str, Any]:
        applied = self._get_applied_migrations()
        pending = self._get_pending_migrations(applied)
        return {
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied": [m.__dict__ for m in applied],
            "pending": [p.name for p in pending],
        }
