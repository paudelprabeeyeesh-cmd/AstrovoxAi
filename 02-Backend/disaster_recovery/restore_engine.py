import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from disaster_recovery.backup_manager import BackupRecord


@dataclass
class RestoreResult:
    backup_id: str
    restored_at: float
    bytes_written: int
    destination: str
    success: bool
    message: str = ""


class RestoreEngine:
    def __init__(self, backup_manager) -> None:
        self._backup_manager = backup_manager
        self._history: List[RestoreResult] = []

    def validate(self, backup_id: str, data: bytes) -> bool:
        record = self._backup_manager.get_backup(backup_id)
        if record is None:
            return False
        return record.checksum == hashlib.sha256(data).hexdigest()

    def restore(self, backup_id: str, destination: str, payload: bytes) -> RestoreResult:
        record = self._backup_manager.get_backup(backup_id)
        if record is None:
            result = RestoreResult(
                backup_id=backup_id,
                restored_at=time.time(),
                bytes_written=0,
                destination=destination,
                success=False,
                message="backup not found",
            )
            self._history.append(result)
            return result

        if not self.validate(backup_id, payload):
            result = RestoreResult(
                backup_id=backup_id,
                restored_at=time.time(),
                bytes_written=0,
                destination=destination,
                success=False,
                message="checksum mismatch",
            )
            self._history.append(result)
            return result

        try:
            with open(destination, "wb") as f:
                f.write(payload)
            result = RestoreResult(
                backup_id=backup_id,
                restored_at=time.time(),
                bytes_written=len(payload),
                destination=destination,
                success=True,
                message="ok",
            )
        except OSError as exc:
            result = RestoreResult(
                backup_id=backup_id,
                restored_at=time.time(),
                bytes_written=0,
                destination=destination,
                success=False,
                message=str(exc),
            )
        self._history.append(result)
        return result

    def list_restore_points(self) -> List[Dict[str, Any]]:
        return [
            {
                "backup_id": r.backup_id,
                "restored_at": r.restored_at,
                "destination": r.destination,
                "success": r.success,
            }
            for r in self._history
        ]
