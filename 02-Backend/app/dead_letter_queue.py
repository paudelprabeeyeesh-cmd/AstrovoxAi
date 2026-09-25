"""Dead letter queue for failed tasks."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class DLQStatus(Enum):
    PENDING = "pending"
    REPROCESSING = "reprocessing"
    FAILED = "failed"
    DEAD = "dead"


@dataclass
class DeadLetter:
    dlq_id: str
    original_task_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    attempts: int = 0
    max_attempts: int = 5
    status: DLQStatus = DLQStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_attempt: Optional[datetime] = None


class DeadLetterQueue:
    _queue: Dict[str, DeadLetter] = {}

    @classmethod
    def enqueue(cls, original_task_id: str, payload: Dict[str, Any], error: str, max_attempts: int = 5) -> DeadLetter:
        dlq_id = f"dlq_{original_task_id}"
        dl = DeadLetter(
            dlq_id=dlq_id,
            original_task_id=original_task_id,
            payload=payload,
            error=error,
            max_attempts=max_attempts,
        )
        cls._queue[dlq_id] = dl
        return dl

    @classmethod
    def dequeue(cls) -> Optional[DeadLetter]:
        for dl in cls._queue.values():
            if dl.status == DLQStatus.PENDING and dl.attempts < dl.max_attempts:
                return dl
        return None

    @classmethod
    def retry(cls, dlq_id: str) -> bool:
        dl = cls._queue.get(dlq_id)
        if not dl:
            return False
        dl.attempts += 1
        dl.last_attempt = datetime.now(timezone.utc)
        if dl.attempts >= dl.max_attempts:
            dl.status = DLQStatus.DEAD
            return False
        dl.status = DLQStatus.PENDING
        return True

    @classmethod
    def mark_failed(cls, dlq_id: str) -> None:
        dl = cls._queue.get(dlq_id)
        if dl:
            dl.status = DLQStatus.FAILED
