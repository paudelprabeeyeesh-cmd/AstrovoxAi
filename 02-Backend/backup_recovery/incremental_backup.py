import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IncrementalBackup:
    backup_id: str
    label: str
    start_time: float
    end_time: Optional[float] = None
    changes: List[bytes] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IncrementalBackupManager:
    def __init__(self) -> None:
        self._backups: Dict[str, IncrementalBackup] = {}
        self._lock = False

    def start_backup(self, label: str = "") -> str:
        if self._lock:
            raise RuntimeError("Backup already in progress")
        self._lock = True
        try:
            backup_id = uuid.uuid4().hex[:12]
            backup = IncrementalBackup(
                backup_id=backup_id,
                label=label,
                start_time=time.time(),
            )
            self._backups[backup_id] = backup
            return backup_id
        finally:
            self._lock = False

    def record_changes(self, backup_id: str, changes: List[bytes]) -> None:
        if backup_id not in self._backups:
            raise KeyError(f"Backup {backup_id} not found")
        backup = self._backups[backup_id]
        if backup.end_time is not None:
            raise RuntimeError(f"Backup {backup_id} already completed")
        backup.changes.extend(changes)

    def complete_backup(self, backup_id: str) -> None:
        if backup_id not in self._backups:
            raise KeyError(f"Backup {backup_id} not found")
        backup = self._backups[backup_id]
        if backup.end_time is not None:
            raise RuntimeError(f"Backup {backup_id} already completed")
        backup.end_time = time.time()
        backup.metadata["total_size"] = sum(len(c) for c in backup.changes)
        backup.metadata["change_count"] = len(backup.changes)

    def get_backup(self, backup_id: str) -> Optional[IncrementalBackup]:
        return self._backups.get(backup_id)

    def list_backups(self) -> List[IncrementalBackup]:
        return list(self._backups.values())
