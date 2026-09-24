"""
Memory Consolidation - Phase 2 Memory Intelligence

Consolidates extracted memories by:
- Merging similar/duplicate memories
- Strengthening high-importance memories
- Consolidating episodic memories into semantic memories
- Pruning redundant or stale memories
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MemoryFragment:
    memory_id: str
    content: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    category: str = "general"
    access_count: int = 0
    is_deleted: bool = False
    consolidated: bool = False
    consolidated_into: Optional[str] = None


class MemoryConsolidator:
    """
    Consolidates memories by merging similar ones and strengthening important memories.
    
    Consolidation strategies:
    - Duplicate detection and merging
    - Episodic-to-semantic consolidation
    - Importance-based strengthening
    - Redundancy pruning
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        consolidation_threshold: float = 0.7,
        stale_days: int = 90,
    ):
        self.similarity_threshold = similarity_threshold
        self.consolidation_threshold = consolidation_threshold
        self.stale_days = stale_days
        self._memories: Dict[str, MemoryFragment] = {}
        self._lock = threading.RLock()

    def add_memory(self, memory: MemoryFragment) -> str:
        """Add a memory fragment for consolidation."""
        with self._lock:
            self._memories[memory.memory_id] = memory
            logger.debug("Added memory fragment: %s", memory.memory_id)
            return memory.memory_id

    def add_memories(self, memories: List[MemoryFragment]) -> List[str]:
        """Add multiple memory fragments."""
        return [self.add_memory(m) for m in memories]

    def _cosine_similarity(self, a: Optional[np.ndarray], b: Optional[np.ndarray]) -> float:
        """Compute cosine similarity between two embeddings."""
        if a is None or b is None:
            return 0.0
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def find_duplicates(self) -> List[Tuple[str, str, float]]:
        """Find pairs of duplicate or near-duplicate memories."""
        duplicates = []
        active = [m for m in self._memories.values() if not m.is_deleted]
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                sim = self._cosine_similarity(active[i].embedding, active[j].embedding)
                if sim >= self.similarity_threshold:
                    duplicates.append((active[i].memory_id, active[j].memory_id, sim))
        return duplicates

    def merge_duplicates(self) -> Dict[str, Any]:
        """Merge duplicate memories, keeping the most important one."""
        duplicates = self.find_duplicates()
        merged = []
        for left_id, right_id, sim in duplicates:
            left = self._memories.get(left_id)
            right = self._memories.get(right_id)
            if not left or not right or left.is_deleted or right.is_deleted:
                continue
            if left.importance >= right.importance:
                keeper, removed = left, right
            else:
                keeper, removed = right, left
            keeper.importance = min(keeper.importance + 0.1, 1.0)
            keeper.last_accessed = datetime.utcnow()
            keeper.access_count += removed.access_count
            removed.is_deleted = True
            removed.consolidated = True
            removed.consolidated_into = keeper.memory_id
            merged.append({
                "kept": keeper.memory_id,
                "merged": removed.memory_id,
                "similarity": sim,
                "new_importance": keeper.importance,
            })
        return {"merged_count": len(merged), "merges": merged}

    def consolidate_episodic_to_semantic(self) -> Dict[str, Any]:
        """Consolidate repeated episodic memories into stronger semantic memories."""
        consolidated = []
        category_groups: Dict[str, List[MemoryFragment]] = {}
        for m in self._memories.values():
            if m.is_deleted or m.consolidated:
                continue
            if m.category == "general":
                category_groups.setdefault(m.content[:50], []).append(m)
        for group in category_groups.values():
            if len(group) < 3:
                continue
            best = max(group, key=lambda m: m.importance + m.access_count * 0.1)
            best.importance = min(best.importance + 0.2, 1.0)
            best.consolidated = True
            best.category = "semantic"
            for m in group:
                if m.memory_id != best.memory_id and not m.is_deleted:
                    m.is_deleted = True
                    m.consolidated = True
                    m.consolidated_into = best.memory_id
            consolidated.append({
                "consolidated_id": best.memory_id,
                "merged_count": len(group),
                "new_importance": best.importance,
            })
        return {"consolidated_count": len(consolidated), "consolidations": consolidated}

    def strengthen_important(self) -> Dict[str, Any]:
        """Strengthen frequently accessed and high-importance memories."""
        strengthened = []
        for m in self._memories.values():
            if m.is_deleted or m.consolidated:
                continue
            old_importance = m.importance
            if m.access_count >= 5:
                m.importance = min(m.importance + 0.15, 1.0)
            elif m.access_count >= 2:
                m.importance = min(m.importance + 0.05, 1.0)
            if m.importance > old_importance:
                strengthened.append({
                    "memory_id": m.memory_id,
                    "old_importance": old_importance,
                    "new_importance": m.importance,
                })
        return {"strengthened_count": len(strengthened), "strengthened": strengthened}

    def prune_stale(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Prune stale, low-importance memories."""
        if now is None:
            now = datetime.utcnow()
        pruned = []
        cutoff = now - timedelta(days=self.stale_days)
        for m in self._memories.values():
            if m.is_deleted or m.consolidated:
                continue
            if m.created_at < cutoff and m.importance < 0.3 and m.access_count < 2:
                m.is_deleted = True
                pruned.append({
                    "memory_id": m.memory_id,
                    "age_days": (now - m.created_at).days,
                    "importance": m.importance,
                })
        return {"pruned_count": len(pruned), "pruned": pruned}

    def consolidate_all(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Run all consolidation strategies."""
        with self._lock:
            duplicates = self.merge_duplicates()
            episodic = self.consolidate_episodic_to_semantic()
            strengthened = self.strengthen_important()
            pruned = self.prune_stale(now)
            total = (
                duplicates["merged_count"]
                + episodic["consolidated_count"]
                + strengthened["strengthened_count"]
                + pruned["pruned_count"]
            )
            active = sum(1 for m in self._memories.values() if not m.is_deleted)
            return {
                "duplicates_merged": duplicates["merged_count"],
                "episodic_consolidated": episodic["consolidated_count"],
                "strengthened": strengthened["strengthened_count"],
                "stale_pruned": pruned["pruned_count"],
                "total_actions": total,
                "active_memories": active,
                "total_memories": len(self._memories),
            }

    def get_active_memories(self) -> List[MemoryFragment]:
        """Get all active (non-deleted) memories."""
        return [m for m in self._memories.values() if not m.is_deleted]

    def get_memory_by_id(self, memory_id: str) -> Optional[MemoryFragment]:
        """Get a memory by ID."""
        m = self._memories.get(memory_id)
        if m and not m.is_deleted:
            m.access_count += 1
            m.last_accessed = datetime.utcnow()
        return m

    def get_stats(self) -> Dict[str, Any]:
        """Get consolidation statistics."""
        active = self.get_active_memories()
        if not active:
            return {"total_memories": 0, "active_memories": 0}
        return {
            "total_memories": len(self._memories),
            "active_memories": len(active),
            "avg_importance": float(np.mean([m.importance for m in active])),
            "avg_access_count": float(np.mean([m.access_count for m in active])),
            "by_category": self._count_by_category(active),
        }

    def _count_by_category(self, memories: List[MemoryFragment]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for m in memories:
            counts[m.category] = counts.get(m.category, 0) + 1
        return counts
