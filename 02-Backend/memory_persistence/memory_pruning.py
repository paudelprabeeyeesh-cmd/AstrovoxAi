"""
Memory Pruning - Task 118

Removes stale or contradicted facts from memory stores.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np


@dataclass
class Memory:
    memory_id: str
    content: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    category: str = "general"
    version: int = 1
    superseded_by: Optional[str] = None
    is_deleted: bool = False
    access_count: int = 0


class MemoryPruner:
    """
    Prunes stale or contradicted memories.
    
    Strategies:
    - Time-based decay (old memories lose importance)
    - Contradiction detection (newer facts supersede older ones)
    - Redundancy removal (duplicate or near-duplicate facts)
    - Low-access eviction
    """

    def __init__(
        self,
        stale_threshold_days: int = 90,
        contradiction_threshold: float = 0.85,
        redundancy_threshold: float = 0.95,
    ):
        self.stale_threshold_days = stale_threshold_days
        self.contradiction_threshold = contradiction_threshold
        self.redundancy_threshold = redundancy_threshold
        self._memories: Dict[str, Memory] = {}

    def add_memory(self, memory: Memory) -> str:
        """Add a memory for pruning management."""
        self._memories[memory.memory_id] = memory
        return memory.memory_id

    def add_memories(self, memories: List[Memory]) -> List[str]:
        """Add multiple memories."""
        return [self.add_memory(m) for m in memories]

    def _compute_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity."""
        if a is None or b is None:
            return 0.0
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def _detect_contradiction(self, text_a: str, text_b: str) -> bool:
        """Simple contradiction detection via negation patterns."""
        negations_a = bool(re.search(r'\b(not|no|never|none|nobody|nothing|nowhere)\b', text_a, re.I))
        negations_b = bool(re.search(r'\b(not|no|never|none|nobody|nothing|nowhere)\b', text_b, re.I))
        if negations_a != negations_b:
            words_a = set(re.findall(r'\w+', text_a.lower()))
            words_b = set(re.findall(r'\w+', text_b.lower()))
            overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
            return overlap > 0.5
        return False

    def _find_contradictions(self) -> List[Tuple[str, str]]:
        """Find pairs of contradictory memories."""
        contradictions = []
        memories = [m for m in self._memories.values() if not m.is_deleted]
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                sim = self._compute_similarity(memories[i].embedding, memories[j].embedding)
                if sim >= self.contradiction_threshold:
                    if self._detect_contradiction(memories[i].content, memories[j].content):
                        contradictions.append((memories[i].memory_id, memories[j].memory_id))
        return contradictions

    def prune_stale(self, now: Optional[datetime] = None) -> List[str]:
        """
        Prune memories that are stale based on age and access.
        
        Returns list of pruned memory IDs.
        """
        if now is None:
            now = datetime.utcnow()
        pruned = []
        cutoff = now - timedelta(days=self.stale_threshold_days)
        
        for memory in self._memories.values():
            if memory.is_deleted:
                continue
            (now - memory.created_at).total_seconds() / 86400.0
            access_score = memory.access_count
            if memory.created_at < cutoff and access_score < 2:
                memory.is_deleted = True
                pruned.append(memory.memory_id)
        
        return pruned

    def prune_contradictions(self) -> List[Tuple[str, str, str]]:
        """
        Resolve contradictions by marking older memories as superseded.
        
        Returns list of (older_id, newer_id, newer_id) tuples.
        """
        resolutions = []
        contradictions = self._find_contradictions()
        
        for old_id, new_id in contradictions:
            old_m = self._memories.get(old_id)
            new_m = self._memories.get(new_id)
            if old_m and new_m and not old_m.is_deleted:
                if old_m.created_at < new_m.created_at:
                    old_m.is_deleted = True
                    old_m.superseded_by = new_id
                    resolutions.append((old_id, new_id, new_id))
                else:
                    new_m.is_deleted = True
                    new_m.superseded_by = old_id
                    resolutions.append((new_id, old_id, old_id))
        
        return resolutions

    def prune_redundant(self) -> List[Tuple[str, str]]:
        """
        Remove redundant (near-duplicate) memories, keeping the most important.
        
        Returns list of (pruned_id, kept_id) tuples.
        """
        pruned = []
        memories = [m for m in self._memories.values() if not m.is_deleted]
        removed: Set[str] = set()
        
        for i in range(len(memories)):
            if memories[i].memory_id in removed:
                continue
            for j in range(i + 1, len(memories)):
                if memories[j].memory_id in removed:
                    continue
                sim = self._compute_similarity(memories[i].embedding, memories[j].embedding)
                if sim >= self.redundancy_threshold:
                    if memories[i].importance >= memories[j].importance:
                        memories[j].is_deleted = True
                        removed.add(memories[j].memory_id)
                        pruned.append((memories[j].memory_id, memories[i].memory_id))
                    else:
                        memories[i].is_deleted = True
                        removed.add(memories[i].memory_id)
                        pruned.append((memories[i].memory_id, memories[j].memory_id))
                        break
        
        return pruned

    def prune_all(
        self,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Run all pruning strategies.
        
        Returns summary of actions taken.
        """
        if now is None:
            now = datetime.utcnow()
        
        stale = self.prune_stale(now)
        contradictions = self.prune_contradictions()
        redundant = self.prune_redundant()
        
        return {
            "stale_pruned": len(stale),
            "contradictions_resolved": len(contradictions),
            "redundant_pruned": len(redundant),
            "total_pruned": len(stale) + len(contradictions) + len(redundant),
            "remaining_active": sum(1 for m in self._memories.values() if not m.is_deleted),
        }

    def get_active_memories(self) -> List[Memory]:
        """Get all active (non-deleted) memories."""
        return [m for m in self._memories.values() if not m.is_deleted]
