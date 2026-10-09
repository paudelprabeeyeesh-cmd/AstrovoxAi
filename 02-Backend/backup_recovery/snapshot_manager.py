import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Snapshot:
    backup_id: str
    timestamp: float
    size_bytes: int
    checksum: str
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SnapshotManager:
    def __init__(self) -> None:
        self._snapshots: List[Snapshot] = []
        self._lock = False

    def create_snapshot(self, data: bytes, label: str = "") -> Snapshot:
        if self._lock:
            raise RuntimeError("Snapshot already in progress")
        self._lock = True
        try:
            ts = time.time()
            backup_id = uuid.uuid4().hex[:12]
            checksum = hashlib.sha256(data).hexdigest()
            snapshot = Snapshot(
                backup_id=backup_id,
                timestamp=ts,
                size_bytes=len(data),
                checksum=checksum,
                label=label,
                metadata={"created": datetime.utcfromtimestamp(ts).isoformat()},
            )
            self._snapshots.append(snapshot)
            self._snapshots.sort(key=lambda s: s.timestamp)
            return snapshot
        finally:
            self._lock = False

    def get_snapshot(self, backup_id: str) -> Optional[Snapshot]:
        for s in self._snapshots:
            if s.backup_id == backup_id:
                return s
        return None

    def list_snapshots(self) -> List[Snapshot]:
        return list(self._snapshots)

    def point_in_time(self, target_ts: float) -> Optional[Snapshot]:
        best = None
        for s in self._snapshots:
            if s.timestamp <= target_ts:
                if best is None or s.timestamp > best.timestamp:
                    best = s
        return best
