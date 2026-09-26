"""Message queue for async processing."""
from __future__ import annotations

import asyncio
import logging
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Message:
    message_id: str
    topic: str
    payload: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0


class MessageQueue:
    def __init__(self, maxsize: int = 10000) -> None:
        self._queues: Dict[str, queue.Queue] = {}
        self._subscribers: Dict[str, List[Callable[..., Any]]] = {}
        self._maxsize = maxsize
        self._dlq: List[Message] = []

    def create_topic(self, topic: str) -> None:
        if topic not in self._queues:
            self._queues[topic] = queue.Queue(maxsize=self._maxsize)

    def publish(self, topic: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> None:
        if topic not in self._queues:
            self.create_topic(topic)
        message = Message(
            message_id=str(__import__("uuid").uuid4()),
            topic=topic,
            payload=payload,
            headers=headers or {},
        )
        self._queues[topic].put(message, block=False)

    def subscribe(self, topic: str, handler: Callable[..., Any]) -> None:
        self._subscribers.setdefault(topic, []).append(handler)

    async def start_consumers(self) -> None:
        tasks = []
        for topic in self._queues:
            task = asyncio.create_task(self._consume_topic(topic))
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _consume_topic(self, topic: str) -> None:
        while True:
            try:
                message = self._queues[topic].get(timeout=1.0)
                for handler in self._subscribers.get(topic, []):
                    try:
                        result = handler(message)
                        if hasattr(result, "__await__"):
                            await result
                    except Exception:
                        logger.exception("Message handler failed for topic %s", topic)
                        message.retry_count += 1
                        if message.retry_count >= 3:
                            self._dlq.append(message)
            except queue.Empty:
                await asyncio.sleep(0.1)

    def get_dlq(self) -> List[Dict[str, Any]]:
        return [
            {
                "message_id": m.message_id,
                "topic": m.topic,
                "retry_count": m.retry_count,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in self._dlq
        ]


message_queue = MessageQueue()
