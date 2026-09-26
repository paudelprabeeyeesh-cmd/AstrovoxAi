"""Unified memory system orchestrator.

Coordinates all memory layers:
- Short-term (context) memory
- Long-term memory
- Semantic memory
- Episodic memory
- User preferences
- Knowledge graph
- Memory scoring and decay
- Memory summarization
- Conflict detection
- Memory editing and deletion
- Context prioritization
- Automatic memory compression
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MemoryTier(str, Enum):
    """Memory importance tiers."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVED = "archived"


class MemoryCategory(str, Enum):
    """Memory content categories."""
    FACT = "fact"
    PREFERENCE = "preference"
    GOAL = "goal"
    CONTEXT = "context"
    KNOWLEDGE = "knowledge"
    EVENT = "event"
    PROCEDURE = "procedure"
    USER_PREFERENCE = "user_preference"


class ConflictStrategy(str, Enum):
    """Strategies for resolving memory conflicts."""
    NEWEST = "newest"
    MOST_IMPORTANT = "most_important"
    USER_CHOICE = "user_choice"
    MERGE = "merge"


@dataclass
class MemoryFragment:
    """Unified memory entry across all layers."""
    memory_id: str
    user_id: str
    content: str
    category: MemoryCategory
    tier: MemoryTier
    importance: float = 1.0
    confidence: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    decay_rate: float = 0.01
    min_importance: float = 0.01
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    summary: Optional[str] = None
    compressed: bool = False
    parent_id: Optional[str] = None
    version: int = 1
    deleted: bool = False
    deleted_at: Optional[datetime] = None

    def apply_decay(self) -> None:
        age_days = (datetime.now(timezone.utc) - self.accessed_at).total_seconds() / 86400.0
        self.importance = max(self.importance * math.exp(-self.decay_rate * age_days), self.min_importance)

    def access(self) -> None:
        self.access_count += 1
        self.accessed_at = datetime.now(timezone.utc)
        self.importance = min(self.importance * 1.1, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "content": self.content,
            "category": self.category.value,
            "tier": self.tier.value,
            "importance": round(self.importance, 4),
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "tags": self.tags,
            "metadata": self.metadata,
            "summary": self.summary,
            "compressed": self.compressed,
            "parent_id": self.parent_id,
            "version": self.version,
            "deleted": self.deleted,
        }


@dataclass
class KnowledgeNode:
    """Node in the knowledge graph."""
    node_id: str
    name: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class KnowledgeEdge:
    """Edge in the knowledge graph."""
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeGraph:
    """Knowledge graph for memory relationships."""

    def __init__(self):
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: Dict[str, KnowledgeEdge] = {}
        self._adjacency: Dict[str, List[str]] = {}

    def add_node(self, node: KnowledgeNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, edge: KnowledgeEdge) -> None:
        self._edges[edge.edge_id] = edge
        self._adjacency.setdefault(edge.source_id, []).append(edge.target_id)
        self._adjacency.setdefault(edge.target_id, []).append(edge.source_id)

    def get_neighbors(self, node_id: str) -> List[str]:
        return list(self._adjacency.get(node_id, []))

    def traverse(self, node_id: str, depth: int = 2) -> List[KnowledgeNode]:
        visited = set()
        queue = [(node_id, 0)]
        result = []
        while queue:
            current, d = queue.pop(0)
            if current in visited or d > depth:
                continue
            visited.add(current)
            node = self._nodes.get(current)
            if node:
                result.append(node)
            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, d + 1))
        return result

    def query(self, subject: str = None, predicate: str = None, obj: str = None) -> List[KnowledgeEdge]:
        results = []
        for edge in self._edges.values():
            if subject and edge.source_id != subject:
                continue
            if predicate and edge.relation != predicate:
                continue
            if obj and edge.target_id != obj:
                continue
            results.append(edge)
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "avg_degree": sum(len(v) for v in self._adjacency.values()) / max(len(self._adjacency), 1),
        }


class MemoryScorer:
    """Score memory importance using multiple heuristics."""

    def score(
        self,
        content: str,
        category: MemoryCategory,
        user_explicit: bool = False,
        access_count: int = 0,
        confidence: float = 1.0,
    ) -> float:
        score = 0.0
        if user_explicit:
            score += 0.4
        score += min(access_count * 0.05, 0.2)
        score += confidence * 0.2
        if category in (MemoryCategory.USER_PREFERENCE, MemoryCategory.PREFERENCE):
            score += 0.2
        elif category == MemoryCategory.GOAL:
            score += 0.15
        content_lower = content.lower()
        high_importance = ["important", "critical", "essential", "must", "required", "remember"]
        low_importance = ["just", "only", "maybe", "perhaps", "might", "temporary"]
        high_count = sum(1 for kw in high_importance if kw in content_lower)
        low_count = sum(1 for kw in low_importance if kw in content_lower)
        score += (high_count * 0.1) - (low_count * 0.1)
        return min(max(score, 0.0), 1.0)


class MemoryCompressor:
    """Compress memory content for storage efficiency."""

    @staticmethod
    def compress(content: str, target_ratio: float = 0.5) -> str:
        if len(content) <= 100:
            return content
        sentences = content.replace("! ", "!\n").replace("? ", "?\n").replace(". ", ".\n").split("\n")
        keep = max(1, int(len(sentences) * target_ratio))
        return " ".join(sentences[:keep])

    @staticmethod
    def summarize_for_context(content: str, max_chars: int = 500) -> str:
        if len(content) <= max_chars:
            return content
        return content[: max_chars - 3] + "..."


class ConflictDetector:
    """Detect and resolve conflicting memories."""

    def detect_conflicts(self, memories: List[MemoryFragment]) -> List[Tuple[MemoryFragment, MemoryFragment, str]]:
        conflicts = []
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                a, b = memories[i], memories[j]
                if a.user_id != b.user_id:
                    continue
                if a.category != b.category:
                    continue
                if self._is_conflict(a.content, b.content):
                    conflicts.append((a, b, "value_mismatch"))
        return conflicts

    def resolve_conflict(
        self,
        a: MemoryFragment,
        b: MemoryFragment,
        strategy: ConflictStrategy = ConflictStrategy.NEWEST,
    ) -> MemoryFragment:
        if strategy == ConflictStrategy.NEWEST:
            return b if b.updated_at >= a.updated_at else a
        if strategy == ConflictStrategy.MOST_IMPORTANT:
            return a if a.importance >= b.importance else b
        if strategy == ConflictStrategy.MERGE:
            merged = MemoryFragment(
                memory_id=str(uuid.uuid4()),
                user_id=a.user_id,
                content=f"{a.content}\n---\n{b.content}",
                category=a.category,
                tier=MemoryTier.MEDIUM,
                importance=max(a.importance, b.importance),
                parent_id=a.memory_id,
                version=max(a.version, b.version) + 1,
            )
            return merged
        return b

    def _is_conflict(self, a: str, b: str) -> bool:
        if a.lower() == b.lower():
            return False
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        overlap = len(words_a & words_b)
        min_len = min(len(words_a), len(words_b))
        if min_len == 0:
            return False
        return overlap / min_len < 0.5


class MemorySystem:
    """Unified memory system orchestrator."""

    def __init__(self):
        self._memories: Dict[str, MemoryFragment] = {}
        self._user_index: Dict[str, List[str]] = {}
        self._knowledge_graph = KnowledgeGraph()
        self._scorer = MemoryScorer()
        self._compressor = MemoryCompressor()
        self._conflict_detector = ConflictDetector()
        self._auto_compress_enabled = True
        self._compression_threshold = 1000

    def remember(
        self,
        user_id: str,
        content: str,
        category: MemoryCategory = MemoryCategory.FACT,
        tier: MemoryTier = MemoryTier.MEDIUM,
        importance: float = 1.0,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_explicit: bool = False,
    ) -> MemoryFragment:
        memory_id = f"mem_{user_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        if user_explicit:
            tier = MemoryTier.HIGH
            importance = max(importance, 0.7)
        score = self._scorer.score(content, category, user_explicit=user_explicit, confidence=confidence)
        fragment = MemoryFragment(
            memory_id=memory_id,
            user_id=user_id,
            content=content,
            category=category,
            tier=tier,
            importance=importance if importance > score else score,
            confidence=confidence,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._memories[memory_id] = fragment
        self._user_index.setdefault(user_id, []).append(memory_id)
        if self._auto_compress_enabled and len(content) > self._compression_threshold:
            fragment.content = self._compressor.compress(content)
            fragment.compressed = True
            fragment.summary = self._compressor.summarize_for_context(content)
        return fragment

    def recall(
        self,
        user_id: str,
        query: str = "",
        category: Optional[MemoryCategory] = None,
        tier: Optional[MemoryTier] = None,
        limit: int = 10,
    ) -> List[MemoryFragment]:
        candidates = []
        memory_ids = self._user_index.get(user_id, [])
        for memory_id in memory_ids:
            frag = self._memories.get(memory_id)
            if not frag or frag.deleted:
                continue
            if category and frag.category != category:
                continue
            if tier and frag.tier != tier:
                continue
            if query and query.lower() not in frag.content.lower():
                continue
            frag.access()
            candidates.append(frag)
        candidates.sort(key=lambda f: f.importance * math.exp(-(time.time() - f.accessed_at) / 86400), reverse=True)
        return candidates[:limit]

    def get_memory(self, memory_id: str) -> Optional[MemoryFragment]:
        frag = self._memories.get(memory_id)
        if frag and not frag.deleted:
            frag.access()
            return frag
        return None

    def edit_memory(self, memory_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[MemoryFragment]:
        frag = self._memories.get(memory_id)
        if not frag or frag.deleted:
            return None
        frag.content = content
        frag.metadata = {**(frag.metadata or {}), **(metadata or {})}
        frag.updated_at = datetime.now(timezone.utc)
        frag.version += 1
        frag.importance = min(frag.importance * 1.2, 1.0)
        return frag

    def delete_memory(self, memory_id: str, soft: bool = True) -> bool:
        frag = self._memories.get(memory_id)
        if not frag:
            return False
        if soft:
            frag.deleted = True
            frag.deleted_at = datetime.now(timezone.utc)
        else:
            self._memories.pop(memory_id, None)
        return True

    def add_user_preference(self, user_id: str, key: str, value: Any) -> MemoryFragment:
        content = f"{key}: {value}"
        return self.remember(
            user_id=user_id,
            content=content,
            category=MemoryCategory.USER_PREFERENCE,
            tier=MemoryTier.HIGH,
            user_explicit=True,
            metadata={"preference_key": key, "preference_value": value},
        )

    def get_user_preferences(self, user_id: str) -> List[MemoryFragment]:
        return self.recall(user_id, category=MemoryCategory.USER_PREFERENCE)

    def add_knowledge_node(self, node: KnowledgeNode) -> None:
        self._knowledge_graph.add_node(node)

    def add_knowledge_edge(self, edge: KnowledgeEdge) -> None:
        self._knowledge_graph.add_edge(edge)

    def get_related_knowledge(self, node_id: str, depth: int = 2) -> List[KnowledgeNode]:
        return self._knowledge_graph.traverse(node_id, depth=depth)

    def detect_conflicts(self, user_id: str) -> List[Tuple[MemoryFragment, MemoryFragment, str]]:
        memories = [self._memories[mid] for mid in self._user_index.get(user_id, []) if mid in self._memories and not self._memories[mid].deleted]
        return self._conflict_detector.detect_conflicts(memories)

    def resolve_conflicts(self, user_id: str, strategy: ConflictStrategy = ConflictStrategy.NEWEST) -> List[MemoryFragment]:
        conflicts = self.detect_conflicts(user_id)
        resolved = []
        for a, b, ctype in conflicts:
            winner = self._conflict_detector.resolve_conflict(a, b, strategy)
            resolved.append(winner)
        return resolved

    def prioritize_context(self, user_id: str, query: str, limit: int = 10) -> List[MemoryFragment]:
        memories = self.recall(user_id, query=query, limit=limit * 2)
        memories.sort(key=lambda f: f.importance * (1 + f.access_count * 0.1), reverse=True)
        return memories[:limit]

    def auto_compress(self, user_id: str) -> int:
        compressed = 0
        for memory_id in self._user_index.get(user_id, []):
            frag = self._memories.get(memory_id)
            if not frag or frag.deleted or frag.compressed:
                continue
            if len(frag.content) > self._compression_threshold:
                frag.content = self._compressor.compress(frag.content)
                frag.compressed = True
                frag.summary = self._compressor.summarize_for_context(frag.content)
                compressed += 1
        return compressed

    def decay_all(self, user_id: str) -> int:
        count = 0
        for memory_id in self._user_index.get(user_id, []):
            frag = self._memories.get(memory_id)
            if frag and not frag.deleted:
                frag.apply_decay()
                count += 1
        return count

    def prune(self, user_id: str, threshold: float = 0.05) -> List[str]:
        removed = []
        for memory_id in list(self._user_index.get(user_id, [])):
            frag = self._memories.get(memory_id)
            if frag and frag.importance < threshold:
                self.delete_memory(memory_id, soft=True)
                removed.append(memory_id)
        return removed

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        memories = [self._memories[mid] for mid in self._user_index.get(user_id, []) if mid in self._memories and not self._memories[mid].deleted]
        return {
            "total": len(memories),
            "by_category": {c.value: sum(1 for m in memories if m.category == c) for c in MemoryCategory},
            "by_tier": {t.value: sum(1 for m in memories if m.tier == t) for t in MemoryTier},
            "compressed": sum(1 for m in memories if m.compressed),
            "knowledge_graph": self._knowledge_graph.get_stats(),
        }


_memory_system: Optional[MemorySystem] = None


def get_memory_system() -> MemorySystem:
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem()
    return _memory_system
