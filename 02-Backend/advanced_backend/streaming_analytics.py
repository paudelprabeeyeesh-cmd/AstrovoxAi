import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Event:
    topic: str
    payload: Any
    timestamp: float = field(default_factory=time.time)
    partition_key: Optional[str] = None


class EventStream:
    def __init__(self, retention_seconds: float = 3600.0, max_events: int = 10000) -> None:
        self._retention = retention_seconds
        self._max_events = max_events
        self._events: Dict[str, deque] = defaultdict(deque)
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = defaultdict(list)
        self._lock = Lock()
        self._offsets: Dict[str, int] = defaultdict(int)

    def publish(self, event: Event) -> None:
        with self._lock:
            topic_store = self._events[event.topic]
            topic_store.append(event)
            self._prune(event.topic)
            for handler in list(self._subscribers.get(event.topic, [])):
                try:
                    handler(event)
                except Exception:
                    pass

    def subscribe(self, topic: str, handler: Callable[[Event], None]) -> None:
        with self._lock:
            self._subscribers[topic].append(handler)

    def consume(self, topic: str, timeout: float = 1.0) -> Optional[Event]:
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                store = self._events[topic]
                if self._offsets[topic] < len(store):
                    event = store[self._offsets[topic]]
                    self._offsets[topic] += 1
                    return event
            time.sleep(0.005)
        return None

    def _prune(self, topic: str) -> None:
        cutoff = time.time() - self._retention
        store = self._events[topic]
        while store and store[0].timestamp < cutoff:
            store.popleft()
        while len(store) > self._max_events:
            store.popleft()

    def analytics(self, topic: str, window_seconds: float = 60.0) -> Dict[str, Any]:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            events = [e for e in self._events.get(topic, []) if e.timestamp >= cutoff]
        counts: Dict[str, int] = defaultdict(int)
        for e in events:
            counts[e.topic] += 1
        return {
            "events_in_window": len(events),
            "topic_distribution": dict(counts),
            "throughput_per_sec": len(events) / max(window_seconds, 1e-6),
        }
