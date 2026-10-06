"""Agent working memory: short-term episodic store with TTL."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    entry_type: str = "episodic"
    created: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    importance: float = 1.0
    expires: float | None = None

    def is_expired(self) -> bool:
        if self.expires is None:
            return False
        return time.time() > self.expires

    def to_dict(self) -> dict:
        return {"id": self.id, "content": self.content, "entry_type": self.entry_type,
                "created": self.created, "last_accessed": self.last_accessed,
                "importance": self.importance, "expires": self.expires}


class WorkingMemory:
    """Short-term episodic memory for an agent with TTL and importance."""

    def __init__(self, capacity: int = 1000, default_ttl: float = 3600.0):
        self.capacity = capacity
        self.default_ttl = default_ttl
        self.storage: dict[str, MemoryEntry] = {}
        self.access_order: list[str] = []

    def store(self, content: str, entry_type: str = "episodic",
              ttl: float | None = None, importance: float = 1.0) -> str:
        entry_id = f"{int(time.time() * 1000000)}"
        while entry_id in self.storage:
            entry_id = f"{entry_id}x"
        self.storage[entry_id] = MemoryEntry(id=entry_id, content=content,
                                              entry_type=entry_type, importance=importance,
                                              expires=time.time() + (ttl or self.default_ttl))
        self.access_order.append(entry_id)
        if len(self.storage) > self.capacity:
            self._evict_oldest()
        return entry_id

    def recall(self, key: str) -> MemoryEntry | None:
        entry = self.storage.get(key)
        if entry is not None:
            entry.last_accessed = time.time()
        return entry

    def search(self, query: str, top: int = 10) -> list[MemoryEntry]:
        """Return most relevant stored entries by keyword match."""
        q = query.lower()
        scored = [(e.importance + (0.1 if q in e.content.lower() else 0.0), e)
                  for e in self.storage.values()]
        scored.sort(reverse=True)
        return [e for _, e in scored[:top]]

    def _evict_oldest(self) -> None:
        for key in list(self.access_order):
            entry = self.storage.get(key)
            if entry is None or entry.is_expired():
                del self.storage[key]
                self.access_order.remove(key)
                if len(self.storage) <= self.capacity:
                    break

    def clear(self) -> None:
        self.storage.clear()
        self.access_order.clear()

    def summary(self) -> dict:
        return {"count": len(self.storage), "capacity": self.capacity,
                "ttl_seconds": self.default_ttl}
