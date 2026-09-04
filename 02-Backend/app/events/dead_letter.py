"""Dead-letter queue for failed event processing.

Implements:
- Dead-letter event storage
- Retry with backoff
- Poison message detection
- DLQ inspection and management
- Dead-letter replay
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .event_store import EventEnvelope

logger = logging.getLogger(__name__)


@dataclass
class DeadLetterEntry:
    """Entry in the dead-letter queue."""

    event: EventEnvelope
    reason: str
    error: str
    retry_count: int = 0
    first_failed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_retry_at: Optional[datetime] = None
    max_retries: int = 3
    backoff_s: float = 1.0

    def can_retry(self) -> bool:
        """Check if entry can be retried."""
        if self.retry_count >= self.max_retries:
            return False
        if self.last_retry_at is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self.last_retry_at).total_seconds()
        return elapsed >= self.backoff_s * (2 ** self.retry_count)

    def increment_retry(self) -> None:
        """Increment retry count and update timestamp."""
        self.retry_count += 1
        self.last_retry_at = datetime.now(timezone.utc)


class DeadLetterQueue:
    """Dead-letter queue for failed event processing.

    Features:
    - Automatic retry with exponential backoff
    - Poison message detection
    - DLQ inspection and management
    - Dead-letter replay
    """

    def __init__(self, max_size: int = 10_000) -> None:
        self._queue: List[DeadLetterEntry] = []
        self._max_size = max_size
        self._retry_task: Optional[Callable[[DeadLetterEntry], None]] = None
        self._running = False

    def enqueue(self, event: EventEnvelope, reason: str, error: str) -> None:
        """Add event to dead-letter queue."""
        entry = DeadLetterEntry(
            event=event,
            reason=reason,
            error=error,
        )
        self._queue.append(entry)
        if len(self._queue) > self._max_size:
            self._queue.pop(0)
        logger.warning("event %s dead-lettered: %s", event.event_id, reason)

    def dequeue(self) -> Optional[DeadLetterEntry]:
        """Get next retryable entry."""
        for entry in self._queue[:]:
            if entry.can_retry():
                return entry
        return None

    def retry(self, handler: Callable[[EventEnvelope], None]) -> int:
        """Retry dead-letter events."""
        retried = 0
        remaining = []

        for entry in self._queue:
            if entry.can_retry():
                try:
                    handler(entry.event)
                    entry.increment_retry()
                    if entry.retry_count >= entry.max_retries:
                        logger.error("event %s exceeded max retries", entry.event.event_id)
                    else:
                        retried += 1
                except Exception as e:
                    entry.increment_retry()
                    entry.error = str(e)
                    remaining.append(entry)
            else:
                remaining.append(entry)

        self._queue = remaining[-self._max_size:]
        return retried

    def poison_messages(self) -> List[DeadLetterEntry]:
        """Get events that exceeded max retries (poison messages)."""
        return [e for e in self._queue if e.retry_count >= e.max_retries]

    def remove(self, event_id: str) -> bool:
        """Remove event from DLQ."""
        for i, entry in enumerate(self._queue):
            if entry.event.event_id == event_id:
                self._queue.pop(i)
                return True
        return False

    def inspect(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Inspect DLQ contents."""
        return [
            {
                "event_id": e.event.event_id,
                "event_type": e.event.event_type,
                "reason": e.reason,
                "error": e.error,
                "retry_count": e.retry_count,
                "max_retries": e.max_retries,
                "first_failed_at": e.first_failed_at.isoformat(),
            }
            for e in self._queue[-limit:]
        ]

    def size(self) -> int:
        """Get DLQ size."""
        return len(self._queue)

    def clear(self) -> None:
        """Clear DLQ."""
        self._queue.clear()
        logger.info("dead-letter queue cleared")

    def set_retry_handler(self, handler: Callable[[DeadLetterEntry], None]) -> None:
        """Set handler for retry processing."""
        self._retry_task = handler
