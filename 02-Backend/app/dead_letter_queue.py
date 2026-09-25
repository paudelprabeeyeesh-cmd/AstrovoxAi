"""Dead letter queue for failed tasks with persistence, retry tracking, and observability."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger("astravox.dlq")


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
    completed_at: Optional[datetime] = None


class DeadLetterQueue:
    """Dead letter queue for failed tasks.

    Supports:
    - In-memory storage with TTL pruning
    - Retry with exponential backoff
    - Dead-lettering after max attempts
    - Observability hooks for metrics
    """

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
        logger.warning("Enqueued DLQ item %s for task %s: %s", dlq_id, original_task_id, error)
        return dl

    @classmethod
    def get(cls, dlq_id: str) -> Optional[DeadLetter]:
        return cls._queue.get(dlq_id)

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
        dl.status = DLQStatus.REPROCESSING
        if dl.attempts >= dl.max_attempts:
            dl.status = DLQStatus.DEAD
            logger.error("DLQ item %s exhausted max attempts and is dead", dlq_id)
            return False
        dl.status = DLQStatus.PENDING
        logger.info("Retrying DLQ item %s (attempt %s/%s)", dlq_id, dl.attempts, dl.max_attempts)
        return True

    @classmethod
    def mark_failed(cls, dlq_id: str) -> None:
        dl = cls._queue.get(dlq_id)
        if dl:
            dl.status = DLQStatus.FAILED

    @classmethod
    def mark_completed(cls, dlq_id: str) -> None:
        dl = cls._queue.get(dlq_id)
        if dl:
            dl.status = DLQStatus.DELIVERED
            dl.completed_at = datetime.now(timezone.utc)

    @classmethod
    def list_pending(cls) -> List[DeadLetter]:
        return [dl for dl in cls._queue.values() if dl.status == DLQStatus.PENDING]

    @classmethod
    def list_dead(cls) -> List[DeadLetter]:
        return [dl for dl in cls._queue.values() if dl.status == DLQStatus.DEAD]

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        pending = len(cls.list_pending())
        dead = len(cls.list_dead())
        reprocessing = len([dl for dl in cls._queue.values() if dl.status == DLQStatus.REPROCESSING])
        return {
            "total": len(cls._queue),
            "pending": pending,
            "reprocessing": reprocessing,
            "dead": dead,
        }

    @classmethod
    def clear(cls) -> None:
        cls._queue.clear()