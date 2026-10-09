import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BackupRecord:
    backup_id: str
    label: str
    created_at: float
    size_bytes: int
    checksum: str
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class BackupManager:
    def __init__(self, storage_dir: str = "./backups") -> None:
        self._storage_dir = storage_dir
        self._records: List[BackupRecord] = []
        self._lock = threading.Lock()
        self._scheduled = False
        self._schedule_interval = 0.0
        self._schedule_thread: Optional[threading.Thread] = None

    def _checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def create_backup(self, data: bytes, label: str = "", source: str = "") -> BackupRecord:
        with self._lock:
            backup_id = hashlib.sha256(
                f"{time.time()}{label}{len(data)}".encode()
            ).hexdigest()[:12]
            checksum = self._checksum(data)
            record = BackupRecord(
                backup_id=backup_id,
                label=label,
                created_at=time.time(),
                size_bytes=len(data),
                checksum=checksum,
                source=source,
            )
            self._records.append(record)
            self._records.sort(key=lambda r: r.created_at)
            return record

    def list_backups(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "backup_id": r.backup_id,
                    "label": r.label,
                    "created_at": r.created_at,
                    "size_bytes": r.size_bytes,
                    "checksum": r.checksum,
                    "source": r.source,
                }
                for r in self._records
            ]

    def get_backup(self, backup_id: str) -> Optional[BackupRecord]:
        with self._lock:
            for r in self._records:
                if r.backup_id == backup_id:
                    return r
            return None

    def delete_backup(self, backup_id: str) -> bool:
        with self._lock:
            for i, r in enumerate(self._records):
                if r.backup_id == backup_id:
                    self._records.pop(i)
                    return True
            return False

    def schedule_backup(self, interval_seconds: float, callback) -> None:
        with self._lock:
            if self._scheduled:
                raise RuntimeError("Backup schedule already active")
            self._schedule_interval = interval_seconds
            self._scheduled = True

        def _run() -> None:
            while self._scheduled:
                callback()
                time.sleep(self._schedule_interval)

        self._schedule_thread = threading.Thread(target=_run, daemon=True)
        self._schedule_thread.start()

    def stop_schedule(self) -> None:
        with self._lock:
            self._scheduled = False
        if self._schedule_thread is not None:
            self._schedule_thread.join(timeout=2.0)
            self._schedule_thread = None
