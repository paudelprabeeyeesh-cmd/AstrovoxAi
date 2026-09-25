"""Memory systems: semantic, episodic, short-term, long-term."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    id: str
    content: str
    memory_type: str
    importance: float = 1.0
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Memory:
    """Multi-type memory system."""

    def __init__(self, max_entries: int = 10000) -> None:
        self._max_entries = max_entries
        self._entries: Dict[str, MemoryEntry] = {}
        self._by_type: Dict[str, List[str]] = {}

    def store(self, content: str, memory_type: str, importance: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> MemoryEntry:
        entry = MemoryEntry(
            id=f"mem_{int(time.time() * 1000)}_{hash(content) % 10000}",
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {},
        )
        self._entries[entry.id] = entry
        self._by_type.setdefault(memory_type, []).append(entry.id)
        if len(self._entries) > self._max_entries:
            self._prune()
        return entry

    def recall(self, query: str, memory_type: Optional[str] = None, limit: int = 10) -> List[MemoryEntry]:
        candidates = []
        search_ids = self._by_type.get(memory_type, list(self._entries.keys())) if memory_type else list(self._entries.keys())
        for mem_id in search_ids:
            entry = self._entries.get(mem_id)
            if entry and query.lower() in entry.content.lower():
                entry.access_count += 1
                entry.accessed_at = time.time()
                candidates.append(entry)
        candidates.sort(key=lambda e: (e.importance, e.access_count), reverse=True)
        return candidates[:limit]

    def _prune(self) -> None:
        sorted_entries = sorted(self._entries.values(), key=lambda e: (e.importance, e.accessed_at))
        for entry in sorted_entries[: len(sorted_entries) // 10]:
            del self._entries[entry.id]
            type_list = self._by_type.get(entry.memory_type, [])
            if entry.id in type_list:
                type_list.remove(entry.id)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "by_type": {k: len(v) for k, v in self._by_type.items()},
        }


_memory = Memory()


def get_memory() -> Memory:
    return _memory
