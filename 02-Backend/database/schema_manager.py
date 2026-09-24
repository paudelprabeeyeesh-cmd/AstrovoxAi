import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class SchemaManager:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
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

    def pending(self, migrations: List[Tuple[int, str, str]]) -> List[Tuple[int, str, str]]:
        applied = set(self.applied_versions())
        return [m for m in migrations if m[0] not in applied]

    def run(self, migrations: List[Tuple[int, str, str]]) -> None:
        pending = self.pending(migrations)
        for version, name, sql in pending:
            self.conn.executescript(sql)
            self.conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.now().isoformat()),
            )
            self.conn.commit()

    def create_table(self, table_name: str, columns: Dict[str, str]) -> None:
        col_defs = ", ".join(f"{name} {definition}" for name, definition in columns.items())
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})"
        self.conn.execute(sql)
        self.conn.commit()

    def add_column(self, table_name: str, column_name: str, definition: str) -> None:
        existing = [
            row[1]
            for row in self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        ]
        if column_name not in existing:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
            self.conn.execute(sql)
            self.conn.commit()
