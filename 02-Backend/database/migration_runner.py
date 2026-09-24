import sqlite3
from datetime import datetime
from typing import List, Optional


class MigrationRunner:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def applied_versions(self) -> List[int]:
        rows = self.conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version ASC"
        ).fetchall()
        return [r["version"] for r in rows]

    def run(self, migrations: List[tuple]) -> None:
        applied = set(self.applied_versions())
        for version, name, sql in migrations:
            if version in applied:
                continue
            self.conn.executescript(sql)
            self.conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.utcnow().isoformat()),
            )
            self.conn.commit()

    def pending(self, migrations: List[tuple]) -> List[tuple]:
        applied = set(self.applied_versions())
        return [m for m in migrations if m[0] not in applied]
