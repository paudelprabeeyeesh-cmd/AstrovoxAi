"""Backup system for Astrovox."""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Backup:
    """A backup entry."""
    id: str
    path: str
    size: int = 0
    created: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        return {"id": self.id, "path": self.path, "size": self.size}


class BackupSystem:
    """Automated backup system."""

    def __init__(self, backup_dir: str = "backups", keep_count: int = 7):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.keep_count = keep_count
        self.backups: list[Backup] = []

    def backup(self, source: str, name: str | None = None) -> Backup:
        dest = self.backup_dir / f"{name or 'backup'}_{int(time.time())}.tar"
        shutil.make_archive(str(dest.with_suffix("")), "tar", source_dir=source or ".")
        size = dest.stat().st_size
        b = Backup(id=f"backup_{len(self.backups)}", path=str(dest), size=size)
        self.backups.append(b)
        self._prune()
        return b

    def _prune(self) -> None:
        while len(self.backups) > self.keep_count:
            old = self.backups.pop(0)
            if Path(old.path).exists():
                Path(old.path).unlink()

    def restore(self, backup_id: str, dest: str) -> bool:
        b = next((x for x in self.backups if x.id == backup_id), None)
        if b is None:
            return False
        shutil.copy2(b.path, dest)
        return True

    def list_backups(self) -> list[Backup]:
        return self.backups

    def count(self) -> int:
        return len(self.backups)
