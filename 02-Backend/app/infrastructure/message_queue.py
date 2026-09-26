"""Message queue infrastructure."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

from app.infrastructure.queue import MessageQueue, Message

logger = logging.getLogger(__name__)


@dataclass
class QueueConfig:
    name: str
    durable: bool = True
    auto_delete: bool = False
    max_priority: Optional[int] = None


class QueueManager:
    """Manages message queues and workers."""

    def __init__(self) -> None:
        self._queue = get_message_queue()
        self._queues: Dict[str, QueueConfig] = {}

    def register_queue(self, config: QueueConfig) -> None:
        self._queues[config.name] = config
        self._queue.declare_queue(config.name, durable=config.durable)
        logger.info(f"Registered queue: {config.name}")

    def publish(self, queue_name: str, payload: Dict[str, Any], headers: Optional[Dict[str, Any]] = None) -> str:
        if queue_name not in self._queues:
            raise ValueError(f"Queue not registered: {queue_name}")
        return self._queue.publish(queue_name, payload, headers)

    def subscribe(self, queue_name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        if queue_name not in self._queues:
            raise ValueError(f"Queue not registered: {queue_name}")
        self._queue.consume(queue_name, handler)

    def start_worker(self, queue_name: str) -> None:
        logger.info(f"Starting worker for queue: {queue_name}")
        self._queue.start_consuming()

    def stop_worker(self) -> None:
        self._queue.stop_consuming()

    def close(self) -> None:
        self._queue.close()


_message_queue_manager: Optional[QueueManager] = None


def get_queue_manager() -> QueueManager:
    global _message_queue_manager
    if _message_queue_manager is None:
        _message_queue_manager = QueueManager()
    return _message_queue_manager
