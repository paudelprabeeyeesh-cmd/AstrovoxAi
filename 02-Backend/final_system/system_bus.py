"""
System-wide message bus with topics, history, and wildcard subscriptions.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


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


class SystemBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[TopicHandler]] = defaultdict(list)
        self._lock = threading.RLock()
        self._history: List[Message] = []
        self._max_history: int = 1000
        self._running = False
        self._last_delivered: Dict[str, Optional[str]] = {}
        self._wildcards: List[Tuple[str, TopicHandler]] = []

    def subscribe(self, topic: str, handler: TopicHandler) -> None:
        with self._lock:
            if topic.endswith(".*"):
                prefix = topic[:-1]
                self._wildcards.append((prefix, handler))
            else:
                self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: TopicHandler) -> None:
        with self._lock:
            if topic.endswith(".*"):
                self._wildcards = [(p, h) for p, h in self._wildcards if h is not handler]
            else:
                self._subscribers[topic] = [h for h in self._subscribers[topic] if h is not handler]

    def publish(self, message: Message) -> None:
        with self._lock:
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            self._deliver(message)
            self._last_delivered[message.topic] = message.timestamp

    def _deliver(self, message: Message) -> None:
        with self._lock:
            handlers = list(self._subscribers.get(message.topic, []))
            for prefix, handler in self._wildcards:
                if message.topic.startswith(prefix):
                    handlers.append(handler)
        for handler in handlers:
            try:
                handler(message)
            except Exception:
                continue

    def history(self, topic: Optional[str] = None) -> List[Message]:
        with self._lock:
            if topic is None:
                return list(self._history)
            return [m for m in self._history if m.topic == topic]

    def last_delivered(self, topic: str) -> Optional[str]:
        return self._last_delivered.get(topic)

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
