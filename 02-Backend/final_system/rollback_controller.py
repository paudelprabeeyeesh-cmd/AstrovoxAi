"""
Controls rollback operations to previous system states.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


class RollbackStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class RollbackRecord:
    target_version: str
    steps: List[str] = field(default_factory=list)
    status: RollbackStatus = RollbackStatus.PENDING
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None


class RollbackController:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._history: List[RollbackRecord] = []

    def initiate(self, target_version: str, steps: Optional[List[str]] = None) -> RollbackRecord:
        record = RollbackRecord(target_version=target_version, steps=steps or [])
        with self._lock:
            self._history.append(record)
        return record

    def execute(self, record: RollbackRecord, runner: Callable[[str], None]) -> RollbackRecord:
        record.status = RollbackStatus.IN_PROGRESS
        record.started_at = datetime.utcnow().isoformat()
        try:
            for step in record.steps:
                runner(step)
            record.status = RollbackStatus.COMPLETED
        except Exception as _e:  # noqa: BLE001
            record.status = RollbackStatus.FAILED
            record.error = str(_e)
        record.finished_at = datetime.utcnow().isoformat()
        return record

    def history(self) -> List[RollbackRecord]:
        with self._lock:
            return list(self._history)
