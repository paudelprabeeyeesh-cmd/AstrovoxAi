"""ACDOS Distributed Memory: shared agent memory, memory synchronization,
knowledge graph storage, semantic indexing, vector sync, memory aging,
memory analytics, conflict resolution.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from . import make_id, now, now_iso
from ..logging_config import get_logger

logger = get_logger(__name__)


class MemoryType(str, Enum):
    WORKING = "working"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    SHARED = "shared"


class ConflictResolution(str, Enum):
    LAST_WRITE_WINS = "last_write_wins"
    MERGE = "merge"
    MANUAL = "manual"
    VECTOR_CLOCK = "vector_clock"


@dataclass
class MemoryItem:
    id: str
    type: MemoryType
    content: Any
    owner: str
    importance: float = 1.0
    confidence: float = 1.0
    created_at: float = field(default_factory=now)
    last_accessed: float = field(default_factory=now)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    vector: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    version: int = 1
    vector_clock: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "owner": self.owner,
            "importance": round(self.importance, 4),
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "tags": self.tags,
            "metadata": self.metadata,
            "session_id": self.session_id,
            "version": self.version,
            "vector_clock": dict(self.vector_clock),
        }

    def score(self) -> float:
        recency = 1.0 / (1.0 + (now() - self.last_accessed) / 3600.0)
        return self.importance * self.confidence * recency


@dataclass
class SyncContext:
    node_id: str
    memory_id: str
    local_version: int
    remote_version: int
    resolution: ConflictResolution
    timestamp: float = field(default_factory=now)


class MemoryLayer:
    def __init__(self, capacity: int = 10000) -> None:
        self._items: Dict[str, MemoryItem] = {}
        self._capacity = capacity
        self._access_order: deque = deque()
        self._lock = threading.Lock()

    def add(self, item: MemoryItem) -> None:
        with self._lock:
            if item.id in self._items:
                self._access_order.remove(item.id)
            self._items[item.id] = item
            self._access_order.append(item.id)
            if len(self._access_order) > self._capacity:
                evicted = self._access_order.popleft()
                self._items.pop(evicted, None)

    def get(self, item_id: str) -> Optional[MemoryItem]:
        with self._lock:
            item = self._items.get(item_id)
            if item:
                item.last_accessed = now()
                item.access_count += 1
                self._access_order.remove(item.id)
                self._access_order.append(item.id)
            return item

    def update(self, item: MemoryItem) -> bool:
        with self._lock:
            if item.id not in self._items:
                return False
            item.version += 1
            item.updated_at = now()
            self._items[item.id] = item
            self._access_order.remove(item.id)
            self._access_order.append(item.id)
            return True

    def delete(self, item_id: str) -> bool:
        with self._lock:
            if item_id in self._items:
                self._items.pop(item_id, None)
                try:
                    self._access_order.remove(item_id)
                except ValueError:
                    pass
                return True
            return False

    def list(self) -> List[MemoryItem]:
        with self._lock:
            return list(self._items.values())

    def search(self, query: str, *, limit: int = 10) -> List[MemoryItem]:
        terms = [t.lower() for t in query.split() if t]
        scored: List[Tuple[float, MemoryItem]] = []
        with self._lock:
            for item in self._items.values():
                text = " ".join(
                    [str(item.content), " ".join(item.tags)]
                ).lower()
                if not terms:
                    continue
                score = sum(1 for term in terms if term in text)
                if score > 0:
                    scored.append((score * item.score(), item))
        scored.sort(key=lambda kv: -kv[0])
        return [item for _, item in scored[:limit]]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._items),
                "capacity": self._capacity,
            }


class WorkingMemory(MemoryLayer):
    def __init__(self, capacity: int = 1000) -> None:
        super().__init__(capacity=capacity)


class LongTermMemory(MemoryLayer):
    def __init__(self, capacity: int = 100000) -> None:
        super().__init__(capacity=capacity)

    def consolidate(self, min_importance: float = 0.8) -> int:
        """Boost importance of frequently accessed items."""
        count = 0
        with self._lock:
            for item in self._items.values():
                if item.access_count >= 5 and item.importance < min_importance:
                    item.importance = min(min_importance, item.importance + 0.1)
                    count += 1
        return count

    def prune(self, threshold: float = 0.1) -> int:
        """Remove low-importance items."""
        count = 0
        with self._lock:
            to_remove = [
                k for k, v in self._items.items()
                if v.score() < threshold
            ]
            for k in to_remove:
                del self._items[k]
                count += 1
        return count


class EpisodicMemory(MemoryLayer):
    def __init__(self, capacity: int = 5000) -> None:
        super().__init__(capacity=capacity)

    def add_event(self, item: MemoryItem) -> None:
        if item.type != MemoryType.EPISODIC:
            item.type = MemoryType.EPISODIC
        self.add(item)

    def by_session(self, session_id: str) -> List[MemoryItem]:
        with self._lock:
            return [item for item in self._items.values() if item.session_id == session_id]

    def timeline(self, start: float, end: float) -> List[MemoryItem]:
        with self._lock:
            return [
                item for item in self._items.values()
                if start <= item.created_at <= end
            ]


class SemanticMemory(MemoryLayer):
    def __init__(self, capacity: int = 50000) -> None:
        super().__init__(capacity=capacity)

    def upsert(self, fact: MemoryItem) -> None:
        if fact.type != MemoryType.SEMANTIC:
            fact.type = MemoryType.SEMANTIC
        self.add(fact)

    def by_tag(self, tag: str) -> List[MemoryItem]:
        with self._lock:
            return [item for item in self._items.values() if tag in item.tags]


class ProceduralMemory(MemoryLayer):
    def __init__(self, capacity: int = 1000) -> None:
        super().__init__(capacity=capacity)

    def add_pattern(self, pattern: MemoryItem) -> None:
        if pattern.type != MemoryType.PROCEDURAL:
            pattern.type = MemoryType.PROCEDURAL
        self.add(pattern)

    def match(self, query: str, *, limit: int = 5) -> List[MemoryItem]:
        return self.search(query, limit=limit)


class SharedMemory:
    """Distributed shared memory with vector clocks and CRDT-like semantics."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._local: Dict[str, MemoryItem] = {}
        self._remote: Dict[str, Dict[str, MemoryItem]] = defaultdict(dict)  # remote_node -> {mem_id: item}
        self._vector_clocks: Dict[str, Dict[str, int]] = defaultdict(dict)  # mem_id -> {node_id: version}
        self._lock = threading.Lock()

    def local_write(self, item: MemoryItem) -> MemoryItem:
        with self._lock:
            item.vector_clock[self.node_id] = item.vector_clock.get(self.node_id, 0) + 1
            item.version += 1
            item.updated_at = now()
            self._local[item.id] = item
            return item

    def receive(self, remote_node: str, item: MemoryItem) -> SyncContext:
        with self._lock:
            local = self._local.get(item.id)
            remote = self._remote[remote_node].get(item.id)

            # Merge vector clocks
            merged_clock = dict(item.vector_clock)
            if local:
                for k, v in local.vector_clock.items():
                    merged_clock[k] = max(merged_clock.get(k, 0), v)
            if remote:
                for k, v in remote.vector_clock.items():
                    merged_clock[k] = max(merged_clock.get(k, 0), v)

            item.vector_clock = merged_clock

            # Determine resolution
            resolution = ConflictResolution.LAST_WRITE_WINS
            local_version = local.version if local else 0
            remote_version = item.version
            if local and remote:
                if local.version > remote_version:
                    resolution = ConflictResolution.LAST_WRITE_WINS
                elif remote_version > local_version:
                    resolution = ConflictResolution.LAST_WRITE_WINS
                else:
                    resolution = ConflictResolution.MERGE

            ctx = SyncContext(
                node_id=self.node_id,
                memory_id=item.id,
                local_version=local_version,
                remote_version=remote_version,
                resolution=resolution,
            )

            self._remote[remote_node][item.id] = item
            self._local[item.id] = item

            return ctx

    def get(self, item_id: str) -> Optional[MemoryItem]:
        with self._lock:
            return self._local.get(item_id)

    def list_local(self) -> List[MemoryItem]:
        with self._lock:
            return list(self._local.values())

    def sync_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "local_count": len(self._local),
                "remote_nodes": len(self._remote),
                "vector_clocks": {k: dict(v) for k, v in self._vector_clocks.items()},
            }


class SemanticIndex:
    """Inverted index for semantic search across memory."""

    def __init__(self) -> None:
        self._postings: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._docs: Dict[str, MemoryItem] = {}
        self._lock = threading.Lock()

    def add(self, item: MemoryItem) -> None:
        with self._lock:
            self._docs[item.id] = item
            tokens = self._tokenize(str(item.content))
            for token in tokens:
                self._postings[token][item.id] += 1

    def remove(self, item_id: str) -> None:
        with self._lock:
            if item_id not in self._docs:
                return
            item = self._docs.pop(item_id)
            tokens = self._tokenize(str(item.content))
            for token in tokens:
                if item_id in self._postings[token]:
                    del self._postings[token][item_id]
                    if not self._postings[token]:
                        del self._postings[token]

    def _tokenize(self, text: str) -> List[str]:
        import re
        return [t.lower() for t in re.findall(r"\w+", text)]

    def search(self, query: str, *, top_k: int = 10) -> List[Tuple[str, float]]:
        with self._lock:
            tokens = self._tokenize(query)
            scores: Dict[str, float] = defaultdict(float)
            for token in tokens:
                for doc_id, tf in self._postings.get(token, {}).items():
                    scores[doc_id] += tf * (1.0 / (1.0 + len(tokens)))
            ranked = sorted(scores.items(), key=lambda x: -x[1])
            return ranked[:top_k]


class MemoryBrain:
    """Unified memory brain orchestrating all memory layers."""

    def __init__(self, node_id: str = "node-1") -> None:
        self.node_id = node_id
        self.working = WorkingMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.shared = SharedMemory(node_id)
        self.semantic_index = SemanticIndex()
        self._lock = threading.Lock()

    def remember(
        self,
        content: Any,
        *,
        type: MemoryType = MemoryType.LONG_TERM,
        importance: float = 1.0,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        vector: Optional[List[float]] = None,
    ) -> MemoryItem:
        item = MemoryItem(
            id=make_id("mem"),
            type=type,
            content=content,
            owner=self.node_id,
            importance=importance,
            tags=tags or [],
            session_id=session_id,
            vector=vector,
        )
        if type == MemoryType.WORKING:
            self.working.add(item)
        elif type == MemoryType.LONG_TERM:
            self.long_term.add(item)
        elif type == MemoryType.EPISODIC:
            self.episodic.add_event(item)
        elif type == MemoryType.SEMANTIC:
            self.semantic.upsert(item)
            self.semantic_index.add(item)
        elif type == MemoryType.PROCEDURAL:
            self.procedural.add_pattern(item)
        return item

    def recall(
        self,
        query: str,
        *,
        types: Optional[List[MemoryType]] = None,
        limit: int = 10,
    ) -> List[MemoryItem]:
        types = types or [MemoryType.LONG_TERM, MemoryType.SEMANTIC, MemoryType.WORKING]
        results: List[MemoryItem] = []
        if MemoryType.LONG_TERM in types:
            results.extend(self.long_term.search(query, limit=limit))
        if MemoryType.SEMANTIC in types:
            results.extend(self.semantic.search(query, limit=limit))
        if MemoryType.WORKING in types:
            results.extend(self.working.search(query, limit=limit))
        if MemoryType.EPISODIC in types:
            results.extend(self.episodic.search(query, limit=limit))
        if MemoryType.PROCEDURAL in types:
            results.extend(self.procedural.match(query, limit=limit))

        # Deduplicate
        seen = set()
        unique: List[MemoryItem] = []
        for item in results:
            if item.id not in seen:
                seen.add(item.id)
                unique.append(item)
        unique.sort(key=lambda it: -it.score())
        return unique[:limit]

    def consolidate(self) -> Dict[str, int]:
        return {
            "long_term_consolidated": self.long_term.consolidate(),
            "long_term_pruned": self.long_term.prune(),
        }

    def sync_with(self, remote_node: str, items: List[MemoryItem]) -> List[SyncContext]:
        contexts: List[SyncContext] = []
        for item in items:
            ctx = self.shared.receive(remote_node, item)
            contexts.append(ctx)
        return contexts

    def stats(self) -> Dict[str, Any]:
        return {
            "working": self.working.stats(),
            "long_term": self.long_term.stats(),
            "episodic": self.episodic.stats(),
            "semantic": self.semantic.stats(),
            "procedural": self.procedural.stats(),
            "shared": self.shared.sync_state(),
        }


# ---------------------------------------------------------------------------
# Global
# ---------------------------------------------------------------------------

_GLOBAL_BRAIN: Optional[MemoryBrain] = None


def get_memory_brain() -> MemoryBrain:
    global _GLOBAL_BRAIN
    if _GLOBAL_BRAIN is None:
        _GLOBAL_BRAIN = MemoryBrain()
    return _GLOBAL_BRAIN