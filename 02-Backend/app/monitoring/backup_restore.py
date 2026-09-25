"""Backup and restore utilities."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import os
import shutil
import json
import gzip
from pathlib import Path


class BackupType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    SNAPSHOT = "snapshot"


class BackupStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Backup:
    backup_id: str
    backup_type: BackupType
    source: str
    destination: str
    size_bytes: int = 0
    status: BackupStatus = BackupStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BackupManager:
    _backups: Dict[str, Backup] = {}

    @classmethod
    def create_backup(cls, backup_type: BackupType, source: str, destination: str) -> Backup:
        backup_id = f"backup_{datetime.now(timezone.utc).timestamp()}"
        backup = Backup(
            backup_id=backup_id,
            backup_type=backup_type,
            source=source,
            destination=destination,
        )
        cls._backups[backup_id] = backup
        return backup

    @classmethod
    def execute_backup(cls, backup_id: str) -> bool:
        backup = cls._backups.get(backup_id)
        if not backup:
            return False
        backup.status = BackupStatus.RUNNING
        try:
            source_path = Path(backup.source)
            if source_path.is_dir():
                shutil.make_archive(backup.destination, "gztar", source_path)
            else:
                with open(backup.destination, "wb") as f_out:
                    with open(source_path, "rb") as f_in:
                        f_out.write(gzip.compress(f_in.read()))
            backup.status = BackupStatus.COMPLETED
            backup.completed_at = datetime.now(timezone.utc)
            return True
        except Exception:
            backup.status = BackupStatus.FAILED
            return False

    @classmethod
    def restore_backup(cls, backup_id: str, target: str) -> bool:
        backup = cls._backups.get(backup_id)
        if not backup or backup.status != BackupStatus.COMPLETED:
            return False
        try:
            if backup.destination.endswith(".tar.gz"):
                shutil.unpack_archive(backup.destination, target)
            else:
                with open(backup.destination, "rb") as f_in:
                    with open(target, "wb") as f_out:
                        f_out.write(gzip.decompress(f_in.read()))
            return True
        except Exception:
            return False
