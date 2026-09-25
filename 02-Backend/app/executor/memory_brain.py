"""Cognitive Memory Brain: working, long-term, episodic, semantic, procedural.

Adds higher-level memory subsystems on top of the basic memory layer:
- Working memory: small, fast, per-session buffer
- Long-term memory: persistent, with consolidation
- Episodic memory: time-stamped events
- Semantic memory: facts with confidence scores
- Procedural memory: how-to patterns
- Forgetting policies
- Memory compression
"""

from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Tuple

from . import make_id, now
from ..logging_config import get_logger

logger = get_logger(__name__)


class MemoryType(str, Enum):
    WORKING = "working"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


@dataclass
class MemoryItem:
    id: str
    type: MemoryType
    content: Any
    importance: float = 1.0
    confidence: float = 1.0
    created_at: float = field(default_factory=now)
    last_accessed: float = field(default_factory=now)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "importance": round(self.importance, 4),
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "tags": self.tags,
            "metadata": self.metadata,
            "session_id": self.session_id,
        }

    def score(self) -> float:
        """Compute a memory score combining recency, importance, and confidence."""

        recency = math.exp(-(now() - self.last_accessed) / 3600.0)
        return self.importance * self.confidence * recency


class WorkingMemory:
    """Per-session short-term buffer with strict capacity."""

    def __init__(self, capacity: int = 32) -> None:
        self._items: Dict[str, MemoryItem] = {}
        self._order: Deque[str] = deque()
        self._capacity = capacity

    def add(self, item: MemoryItem) -> None:
        if item.id in self._items:
            self._order.remove(item.id)
        self._items[item.id] = item
        self._order.append(item.id)
        while len(self._order) > self._capacity:
            evicted = self._order.popleft()
            self._items.pop(evicted, None)

    def get(self, item_id: str) -> Optional[MemoryItem]:
        item = self._items.get(item_id)
        if item is None:
            return None
        item.last_accessed = now()
        item.access_count += 1
        return item

    def list(self) -> List[MemoryItem]:
        return list(self._items.values())

    def clear(self) -> None:
        self._items.clear()
        self._order.clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._items),
            "capacity": self._capacity,
        }


class LongTermMemory:
    """Persistent memory with consolidation and forgetting policies."""

    def __init__(self) -> None:
        self._items: Dict[str, MemoryItem] = {}

    def add(self, item: MemoryItem) -> None:
        if item.type != MemoryType.LONG_TERM:
            item.type = MemoryType.LONG_TERM
        self._items[item.id] = item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        item = self._items.get(item_id)
        if item is None:
            return None
        item.last_accessed = now()
        item.access_count += 1
        return item

    def search(self, query: str, *, limit: int = 10) -> List[MemoryItem]:
        terms = [t.lower() for t in query.split() if t]
        scored: List[Tuple[float, MemoryItem]] = []
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

    def forget(self, threshold: float = 0.05) -> List[str]:
        """Remove items whose combined score has fallen below threshold."""

        forgotten: List[str] = []
        for item in list(self._items.values()):
            if item.score() < threshold:
                del self._items[item.id]
                forgotten.append(item.id)
        return forgotten

    def consolidate(self) -> int:
        """Boost importance of frequently accessed items."""

        count = 0
        for item in self._items.values():
            if item.access_count >= 3 and item.importance < 1.0:
                item.importance = min(1.0, item.importance + 0.1)
                count += 1
        return count

    def stats(self) -> Dict[str, Any]:
        return {"size": len(self._items)}


class EpisodicMemory:
    """Time-ordered event log."""

    def __init__(self, capacity: int = 5000) -> None:
        self._events: Deque[MemoryItem] = deque(maxlen=capacity)
        self._index: Dict[str, MemoryItem] = {}

    def add(self, event: MemoryItem) -> None:
        if event.type != MemoryType.EPISODIC:
            event.type = MemoryType.EPISODIC
        self._events.append(event)
        self._index[event.id] = event

    def recent(self, limit: int = 20) -> List[MemoryItem]:
        return list(self._events)[-limit:]

    def by_session(self, session_id: str) -> List[MemoryItem]:
        return [e for e in self._events if e.session_id == session_id]

    def stats(self) -> Dict[str, Any]:
        return {"events": len(self._events)}


class SemanticMemory:
    """Facts with confidence scores."""

    def __init__(self) -> None:
        self._facts: Dict[str, MemoryItem] = {}

    def upsert(self, fact: MemoryItem) -> None:
        if fact.type != MemoryType.SEMANTIC:
            fact.type = MemoryType.SEMANTIC
        existing = self._facts.get(fact.id)
        if existing is not None:
            # Update with higher confidence wins.
            if fact.confidence > existing.confidence:
                self._facts[fact.id] = fact
        else:
            self._facts[fact.id] = fact

    def get(self, fact_id: str) -> Optional[MemoryItem]:
        return self._facts.get(fact_id)

    def by_tag(self, tag: str) -> List[MemoryItem]:
        return [f for f in self._facts.values() if tag in f.tags]

    def decay(self, rate: float = 0.01) -> int:
        count = 0
        for fact in self._facts.values():
            if fact.confidence > 0:
                fact.confidence = max(0.0, fact.confidence - rate)
                count += 1
        return count

    def stats(self) -> Dict[str, Any]:
        return {"facts": len(self._facts)}


class ProceduralMemory:
    """How-to patterns (step sequences)."""

    def __init__(self) -> None:
        self._patterns: Dict[str, MemoryItem] = {}

    def add(self, pattern: MemoryItem) -> None:
        if pattern.type != MemoryType.PROCEDURAL:
            pattern.type = MemoryType.PROCEDURAL
        self._patterns[pattern.id] = pattern

    def get(self, pattern_id: str) -> Optional[MemoryItem]:
        return self._patterns.get(pattern_id)

    def search(self, query: str, *, limit: int = 5) -> List[MemoryItem]:
        terms = [t.lower() for t in query.split() if t]
        scored: List[Tuple[float, MemoryItem]] = []
        for pattern in self._patterns.values():
            text = " ".join([str(pattern.content), " ".join(pattern.tags)]).lower()
            score = sum(1 for term in terms if term in text)
            if score > 0:
                scored.append((score, pattern))
        scored.sort(key=lambda kv: -kv[0])
        return [p for _, p in scored[:limit]]

    def stats(self) -> Dict[str, Any]:
        return {"patterns": len(self._patterns)}


class MemoryCompression:
    """Compress multiple memory items into a single summary."""

    @staticmethod
    def compress(items: Iterable[MemoryItem], *, max_items: int = 5) -> str:
        items = list(items)[:max_items]
        if not items:
            return ""
        lines = [f"- {item.type.value}: {item.content}" for item in items]
        return "\n".join(lines)


class MemoryBrain:
    """The unified memory brain that orchestrates all layers."""

    def __init__(self) -> None:
        self.working = WorkingMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self._sessions: Dict[str, WorkingMemory] = {}

    def session(self, session_id: str) -> WorkingMemory:
        if session_id not in self._sessions:
            self._sessions[session_id] = WorkingMemory()
        return self._sessions[session_id]

    def remember(
        self,
        content: Any,
        *,
        type: MemoryType = MemoryType.LONG_TERM,
        importance: float = 1.0,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        confidence: float = 1.0,
    ) -> MemoryItem:
        item = MemoryItem(
            id=make_id("mem"),
            type=type,
            content=content,
            importance=importance,
            confidence=confidence,
            tags=tags or [],
            session_id=session_id,
        )
        if type == MemoryType.WORKING:
            target = self.session(session_id) if session_id else self.working
            target.add(item)
        elif type == MemoryType.LONG_TERM:
            self.long_term.add(item)
        elif type == MemoryType.EPISODIC:
            self.episodic.add(item)
        elif type == MemoryType.SEMANTIC:
            self.semantic.upsert(item)
        elif type == MemoryType.PROCEDURAL:
            self.procedural.add(item)
        return item

    def replay(self, session_id: str) -> List[MemoryItem]:
        return self.episodic.by_session(session_id)

    def compress_session(self, session_id: str) -> str:
        items = self.replay(session_id)
        return MemoryCompression.compress(items)

    def consolidate(self) -> Dict[str, int]:
        return {
            "long_term": self.long_term.consolidate(),
            "forgotten": len(self.long_term.forget()),
        }

    def recall(
        self,
        query: str,
        *,
        type: Optional[MemoryType] = None,
        limit: int = 10,
    ) -> List[MemoryItem]:
        results: List[MemoryItem] = []
        if type in (None, MemoryType.LONG_TERM):
            results.extend(self.long_term.search(query, limit=limit))
        if type in (None, MemoryType.PROCEDURAL):
            results.extend(self.procedural.search(query, limit=limit))
        if type in (None, MemoryType.WORKING):
            results.extend(self.working.list())
        if type in (None, MemoryType.SEMANTIC):
            for item in self.semantic._facts.values():
                results.append(item)
        # Deduplicate.
        seen: set[str] = set()
        unique: List[MemoryItem] = []
        for item in results:
            if item.id in seen:
                continue
            seen.add(item.id)
            unique.append(item)
        unique.sort(key=lambda it: -it.score())
        return unique[:limit]

    def stats(self) -> Dict[str, Any]:
        return {
            "working": self.working.stats(),
            "long_term": self.long_term.stats(),
            "episodic": self.episodic.stats(),
            "semantic": self.semantic.stats(),
            "procedural": self.procedural.stats(),
            "sessions": len(self._sessions),
        }


_GLOBAL_BRAIN: Optional[MemoryBrain] = None


def get_memory_brain() -> MemoryBrain:
    global _GLOBAL_BRAIN
    if _GLOBAL_BRAIN is None:
        _GLOBAL_BRAIN = MemoryBrain()
    return _GLOBAL_BRAIN