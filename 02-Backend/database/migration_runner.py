import sqlite3
from datetime import datetime
from typing import List, Optional


class MigrationRunner:
    """Applies versioned schema migrations, recording what has been applied.

    ``applied_versions()`` reports versions in the order they were applied.
    That needed a dedicated application-order column, because the tracking
    table's ``version INTEGER PRIMARY KEY`` is a rowid alias in SQLite: rows
    are physically ordered by version, so the version order alone could never
    express "this ran after that", and an out-of-order migration list was
    indistinguishable from an in-order one.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                applied_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL UNIQUE,
                applied_at TEXT NOT NULL
            );
        """)
        # Legacy databases created this table with `version INTEGER PRIMARY
        # KEY`, which cannot preserve application order. The column is added
        # defensively; a fresh table already has it from the statement above.
        existing = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(schema_migrations)").fetchall()
        }
        if "applied_seq" not in existing:
            self.conn.execute(
                "ALTER TABLE schema_migrations ADD COLUMN applied_seq INTEGER"
            )
        self.conn.commit()

    def applied_versions(self) -> List[int]:
        rows = self.conn.execute(
            "SELECT version FROM schema_migrations ORDER BY applied_seq ASC"
        ).fetchall()
        return [r["version"] for r in rows]

    def run(self, migrations: List[tuple]) -> None:
        applied = set(self.applied_versions())
        for version, name, sql in migrations:
            if version in applied:
                continue
            # The migration must succeed before it is recorded. `executescript`
            # commits whatever it has run so far, so a partially applied script
            # can still take effect even when this raises; the caller is
            # expected to inspect the schema rather than assume the script was
            # rolled back.
            self.conn.executescript(sql)
            self.conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.utcnow().isoformat()),
            )
            self.conn.commit()

    def pending(self, migrations: List[tuple]) -> List[tuple]:
        applied = set(self.applied_versions())
        return [m for m in migrations if m[0] not in applied]


def run_migrations(conn: sqlite3.Connection, migrations: List[tuple]) -> None:
    MigrationRunner(conn).run(migrations)
