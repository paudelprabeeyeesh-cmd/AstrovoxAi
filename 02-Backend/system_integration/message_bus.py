"""
Inter-component message bus.

Provides pub/sub, event delivery, and in-process messaging between components.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple


@dataclass
class Message:
    topic: str
    payload: Any
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


TopicHandler = Callable[[Message], None]


class MessageBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[TopicHandler]] = defaultdict(list)
        self._lock = threading.RLock()
        self._queue: List[Tuple[Message, int]] = []
        self._running = False
        self._last_delivered: Dict[str, Optional[str]] = {}

    def subscribe(self, topic: str, handler: TopicHandler) -> None:
        with self._lock:
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: TopicHandler) -> None:
        with self._lock:
            self._subscribers[topic] = [h for h in self._subscribers[topic] if h is not handler]

    def publish(self, message: Message, priority: int = 0) -> None:
        with self._lock:
            self._queue.append((message, priority))
            self._queue.sort(key=lambda item: item[1], reverse=True)

    def start(self) -> None:
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        while self._running:
            item = None
            with self._lock:
                if self._queue:
                    item = self._queue.pop(0)
            if item:
                message, _ = item
                self._deliver(message)

    def _deliver(self, message: Message) -> None:
        with self._lock:
            handlers = list(self._subscribers.get(message.topic, []))
        for handler in handlers:
            try:
                handler(message)
            except Exception:
                continue
        self._last_delivered[message.topic] = message.timestamp

    def stop(self) -> None:
        self._running = False

    def last_delivered(self, topic: str) -> Optional[str]:
        return self._last_delivered.get(topic)
