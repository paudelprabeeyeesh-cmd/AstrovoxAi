"""Advanced memory with importance scoring and decay."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryImportance(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVED = "archived"


@dataclass
class MemoryFragment:
    memory_id: str
    content: str
    importance: float
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    decay_rate: float = 0.01
    min_importance: float = 0.01

    def apply_decay(self) -> None:
        age_days = (datetime.now(timezone.utc) - self.last_accessed).total_seconds() / 86400.0
        self.importance = max(self.importance * math.exp(-self.decay_rate * age_days), self.min_importance)

    def access(self) -> None:
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)
        self.importance = min(self.importance * 1.1, 1.0)


class ImportanceScoringEngine:
    """Score memory importance using multiple heuristics."""

    def score(self, content: str, context: Dict[str, Any] = None) -> float:
        score = 0.5
        if context:
            if context.get("user_explicit"):
                score += 0.3
            if context.get("frequently_accessed"):
                score += 0.2
        if any(word in content.lower() for word in ["important", "critical", "remember", "key"]):
            score += 0.2
        return max(0.0, min(1.0, score))


class AdvancedMemoryManager:
    """Memory with importance scoring and decay."""

    def __init__(self):
        self._memories: Dict[str, MemoryFragment] = {}
        self._scorer = ImportanceScoringEngine()

    def add(self, memory_id: str, content: str, importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> MemoryFragment:
        fragment = MemoryFragment(
            memory_id=memory_id,
            content=content,
            importance=importance,
            metadata=metadata or {},
        )
        self._memories[memory_id] = fragment
        return fragment

    def get(self, memory_id: str) -> Optional[MemoryFragment]:
        fragment = self._memories.get(memory_id)
        if fragment:
            fragment.access()
        return fragment

    def decay_all(self) -> None:
        for fragment in self._memories.values():
            fragment.apply_decay()

    def prune(self, threshold: float = 0.05) -> List[str]:
        to_remove = [mid for mid, frag in self._memories.items() if frag.importance < threshold]
        for mid in to_remove:
            del self._memories[mid]
        return to_remove

    def search(self, query: str, limit: int = 10) -> List[MemoryFragment]:
        query_terms = set(query.lower().split())
        scored = []
        for fragment in self._memories.values():
            terms = set(fragment.content.lower().split())
            overlap = len(query_terms & terms)
            score = overlap / max(len(query_terms), 1)
            if score > 0:
                scored.append((score * fragment.importance, fragment))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [frag for _, frag in scored[:limit]]
