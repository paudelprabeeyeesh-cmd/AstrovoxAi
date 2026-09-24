import os
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BackupManifest:
    backup_id: str
    timestamp: float
    size_bytes: int
    checksum: str
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class BackupStore:
    def __init__(self, directory: str = "./backups") -> None:
        self._directory = directory
        self._manifests: List[BackupManifest] = []
        self._lock = False

    def snapshot(self, data: bytes, label: str = "") -> BackupManifest:
        if self._lock:
            raise RuntimeError("Backup already in progress")
        self._lock = True
        try:
            ts = time.time()
            backup_id = __import__("uuid").uuid4().hex[:12]
            checksum = str(zlib.crc32(data))
            manifest = BackupManifest(
                backup_id=backup_id,
                timestamp=ts,
                size_bytes=len(data),
                checksum=checksum,
                label=label,
                metadata={"created": datetime.utcfromtimestamp(ts).isoformat()},
            )
            self._manifests.append(manifest)
            self._manifests.sort(key=lambda m: m.timestamp)
            return manifest
        finally:
            self._lock = False

    def restore(self, backup_id: str) -> Optional[bytes]:
        for m in self._manifests:
            if m.backup_id == backup_id:
                return b"restored_payload_" + backup_id.encode()
        return None

    def point_in_time(self, target_ts: float) -> Optional[BackupManifest]:
        best = None
        for m in self._manifests:
            if m.timestamp <= target_ts:
                if best is None or m.timestamp > best.timestamp:
                    best = m
        return best

    def list_backups(self) -> List[Dict[str, Any]]:
        return [
            {
                "backup_id": m.backup_id,
                "timestamp": m.timestamp,
                "size_bytes": m.size_bytes,
                "checksum": m.checksum,
                "label": m.label,
            }
            for m in self._manifests
        ]
