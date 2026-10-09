"""Message queue with backpressure."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueueStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


@dataclass
class QueuedMessage:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    queue_name: str = "default"
    payload: Dict[str, Any] = field(default_factory=dict)
    status: QueueStatus = QueueStatus.PENDING
    priority: int = 0
    retries: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    processed_at: Optional[float] = None
    error: Optional[str] = None


MessageHandler = Callable[[QueuedMessage], Awaitable[None]]


class MessageQueue:
    """Async message queue with dead-letter support."""

    def __init__(self, max_size: int = 1000):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._handlers: Dict[str, MessageHandler] = {}
        self._dead_letters: Dict[str, List[QueuedMessage]] = {}
        self._max_size = max_size
        self._running: Dict[str, bool] = {}

    def ensure_queue(self, queue_name: str) -> asyncio.Queue:
        if queue_name not in self._queues:
            self._queues[queue_name] = asyncio.Queue(maxsize=self._max_size)
            self._dead_letters[queue_name] = []
            self._running[queue_name] = False
        return self._queues[queue_name]

    def register_handler(self, queue_name: str, handler: MessageHandler) -> None:
        self.ensure_queue(queue_name)
        self._handlers[queue_name] = handler

    async def enqueue(self, queue_name: str, payload: Dict[str, Any], priority: int = 0) -> QueuedMessage:
        q = self.ensure_queue(queue_name)
        message = QueuedMessage(queue_name=queue_name, payload=payload, priority=priority)
        await q.put(message)
        logger.debug("Enqueued message %s to %s", message.message_id, queue_name)
        return message

    async def start_worker(self, queue_name: str) -> None:
        q = self.ensure_queue(queue_name)
        handler = self._handlers.get(queue_name)
        if not handler:
            logger.error("No handler registered for queue %s", queue_name)
            return
        self._running[queue_name] = True
        logger.info("Worker started for queue %s", queue_name)
        while self._running.get(queue_name, False):
            message = await q.get()
            message.status = QueueStatus.PROCESSING
            try:
                await handler(message)
                message.status = QueueStatus.COMPLETED
            except Exception as exc:  # noqa: BLE001
                message.error = str(exc)
                message.retries += 1
                if message.retries >= message.max_retries:
                    message.status = QueueStatus.DEAD_LETTERED
                    self._dead_letters[queue_name].append(message)
                    logger.error("Message %s dead-lettered after %d retries", message.message_id, message.retries)
                else:
                    message.status = QueueStatus.FAILED
                    await asyncio.sleep(0.5 * (2 ** message.retries))
                    await q.put(message)
            finally:
                q.task_done()

    async def stop_worker(self, queue_name: str) -> None:
        self._running[queue_name] = False

    def get_dead_letters(self, queue_name: str) -> List[QueuedMessage]:
        return list(self._dead_letters.get(queue_name, []))


message_queue = MessageQueue()
