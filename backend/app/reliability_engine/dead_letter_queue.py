"""Dead letter queue for failed message processing."""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RetryPolicy:
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0, max_delay_seconds: float = 60.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_delay_seconds = max_delay_seconds


class DLQStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DeadLetterMessage:
    message_id: str
    payload: Dict[str, Any]
    reason: str
    original_topic: str
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: DLQStatus = DLQStatus.PENDING
    next_retry_at: Optional[datetime] = None
    error: Optional[str] = None


class DeadLetterQueue:
    def __init__(self, storage_path: str = "/tmp/astrovox_dlq"):
        self.storage_path = storage_path
        self._messages: Dict[str, DeadLetterMessage] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        os.makedirs(storage_path, exist_ok=True)

    def enqueue(self, message: DeadLetterMessage) -> None:
        self._messages[message.message_id] = message
        self._persist(message)

    async def process_next(self, handler: Callable[[Dict[str, Any]], None]) -> Optional[DeadLetterMessage]:
        for msg in self._messages.values():
            if msg.status == DLQStatus.PENDING:
                msg.status = DLQStatus.PROCESSING
                try:
                    handler(msg.payload)
                    msg.status = DLQStatus.COMPLETED
                    return msg
                except Exception as exc:
                    msg.retry_count += 1
                    msg.error = str(exc)
                    msg.status = DLQStatus.FAILED
                    raise
        return None

    def get_failed(self, topic: Optional[str] = None) -> List[DeadLetterMessage]:
        return [
            msg for msg in self._messages.values()
            if msg.status == DLQStatus.FAILED and (topic is None or msg.original_topic == topic)
        ]

    def _persist(self, message: DeadLetterMessage) -> None:
        path = os.path.join(self.storage_path, f"{message.message_id}.json")
        try:
            with open(path, "w") as f:
                json.dump({
                    "message_id": message.message_id,
                    "payload": message.payload,
                    "reason": message.reason,
                    "original_topic": message.original_topic,
                    "retry_count": message.retry_count,
                    "status": message.status.value,
                }, f)
        except OSError:
            logger.exception("failed to persist dlq message")


dead_letter_queue = DeadLetterQueue()
