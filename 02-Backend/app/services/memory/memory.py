"""Memory systems: semantic, episodic, short-term, long-term."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
        self._recall_cache: Dict[str, Tuple[List[MemoryEntry], float]] = {}
        self._RECALL_TTL = 30.0

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
        cache_key = f"{query}:{memory_type}:{limit}"
        now = time.time()
        cached = self._recall_cache.get(cache_key)
        if cached and (now - cached[1]) < self._RECALL_TTL:
            return list(cached[0])
        candidates = []
        search_ids = self._by_type.get(memory_type, list(self._entries.keys())) if memory_type else list(self._entries.keys())
        for mem_id in search_ids:
            entry = self._entries.get(mem_id)
            if entry and query.lower() in entry.content.lower():
                entry.access_count += 1
                entry.accessed_at = time.time()
                candidates.append(entry)
        candidates.sort(key=lambda e: (e.importance, e.access_count), reverse=True)
        result = candidates[:limit]
        self._recall_cache[cache_key] = (result, now)
        return result

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


class VectorIndex:
    def __init__(self) -> None:
        self._store: Dict[str, List[float]] = {}

    def add(self, key: str, vector: List[float]) -> None:
        self._store[key] = vector

    def search(self, query: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        results = []
        for key, vec in self._store.items():
            score = _cosine(query, vec)
            results.append((key, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
