"""Agent memory systems."""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    key: str
    value: Any
    embedding: Optional[list[float]] = None
    timestamp: float = field(default_factory=time.time)
    ttl: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl


class ShortTermMemory:
    def __init__(self, capacity: int = 50):
        self._store: dict[str, MemoryEntry] = {}
        self._order: list[str] = []
        self.capacity = capacity

    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        if key in self._store:
            self._order.remove(key)
        elif len(self._store) >= self.capacity:
            oldest = self._order.pop(0)
            del self._store[oldest]
        self._store[key] = MemoryEntry(key=key, value=value, ttl=ttl)
        self._order.append(key)

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry and not entry.is_expired():
            return entry.value
        if entry:
            del self._store[key]
            self._order.remove(key)
        return None

    def clear(self):
        self._store.clear()
        self._order.clear()


class LongTermMemory:
    def __init__(self):
        self._store: dict[str, MemoryEntry] = {}

    def put(self, key: str, value: Any, metadata: Optional[dict] = None):
        self._store[key] = MemoryEntry(key=key, value=value, metadata=metadata or {})

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        return entry.value if entry else None

    def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        query_lower = query.lower()
        scored = []
        for entry in self._store.values():
            score = 0.0
            if isinstance(entry.value, str) and query_lower in entry.value.lower():
                score += 1.0
            scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]


class SharedMemory:
    def __init__(self):
        self._shared: dict[str, MemoryEntry] = {}

    def broadcast(self, key: str, value: Any):
        self._shared[key] = MemoryEntry(key=key, value=value)

    def read(self, key: str) -> Optional[Any]:
        entry = self._shared.get(key)
        return entry.value if entry else None

    def snapshot(self) -> dict:
        return {k: v.value for k, v in self._shared.items()}


class AgentMemory:
    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.shared = SharedMemory()

    def remember(self, key: str, value: Any, persist: bool = False):
        self.short_term.put(key, value)
        if persist:
            self.long_term.put(key, value)

    def recall(self, key: str) -> Optional[Any]:
        value = self.short_term.get(key)
        if value is not None:
            return value
        return self.long_term.get(key)

    def share(self, key: str, value: Any):
        self.shared.broadcast(key, value)


agent_memory = AgentMemory()
