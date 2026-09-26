"""Backup manifest generator for database backups."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text

logger = logging.getLogger(__name__)


@dataclass
class BackupManifest:
    manifest_version: str = "1.0"
    database_url: str = ""
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: str = ""
    tables: list[str] = field(default_factory=list)
    row_counts: dict[str, int] = field(default_factory=dict)
    checksums: dict[str, str] = field(default_factory=dict)
    size_bytes: int = 0
    files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self, path: Path | str) -> None:
        path = Path(path)
        path.write_text(json.dumps(self.__dict__, indent=2, default=str), encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path | str) -> BackupManifest:
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


class BackupManifestGenerator:
    """Generate a JSON manifest describing a database backup."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url)
        self._inspector = inspect(self._engine)

    def generate(self, backup_dir: Path | str) -> BackupManifest:
        backup_dir = Path(backup_dir)
        tables = self._inspector.get_table_names()
        row_counts: dict[str, int] = {}
        checksums: dict[str, str] = {}
        files: list[str] = []
        total_size = 0
        for table in tables:
            count = self._count_rows(table)
            row_counts[table] = count
            dump_file = backup_dir / f"{table}.sql"
            checksum = self._dump_table(table, dump_file)
            checksums[table] = checksum
            files.append(str(dump_file.name))
            total_size += dump_file.stat().st_size if dump_file.exists() else 0
        manifest = BackupManifest(
            database_url=self._sanitize_url(str(self._engine.url)),
            tables=tables,
            row_counts=row_counts,
            checksums=checksums,
            size_bytes=total_size,
            files=files,
        )
        manifest.finished_at = datetime.utcnow().isoformat()
        manifest.to_json(backup_dir / "manifest.json")
        return manifest

    def _count_rows(self, table: str) -> int:
        with self._engine.connect() as conn:
            row = conn.execute(text(f"SELECT count(*) AS n FROM {table}")).fetchone()
        return row.n if row else 0

    def _dump_table(self, table: str, path: Path) -> str:
        with self._engine.connect() as conn:
            rows = conn.execute(text(f"SELECT * FROM {table}")).fetchall()
        lines = []
        for row in rows:
            lines.append(json.dumps(dict(row._mapping), default=str))
        path.write_text("\n".join(lines), encoding="utf-8")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _sanitize_url(self, url: str) -> str:
        if "@" in url:
            parts = url.split("@")
            return "://***:***@" + parts[-1]
        return url
