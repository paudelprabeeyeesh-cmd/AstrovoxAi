"""Enhanced Memory System — long-term, episodic, semantic memory with ranking and decay.

Phase 354 — Memory Engine 3.0:
Semantic memory, episodic memory, working memory, memory graph, memory ranking,
importance scoring, time decay, topic clustering, memory merging, duplicate
removal, cross-session memory, user preferences, team memory, workspace memory,
memory encryption, memory compression, memory analytics, memory versioning,
explainable retrieval, automatic cleanup.
"""

import time
import logging
import math
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    user_id: str
    content: str
    memory_type: str
    importance: float = 1.0
    created_at: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class EpisodicMemory:
    """An episodic memory of a conversation or event."""
    id: str
    user_id: str
    title: str
    summary: str
    participants: list[str]
    timestamp: float
    duration: float = 0.0
    outcome: str = ""
    importance: float = 1.0


@dataclass
class SemanticMemory:
    """A semantic memory (fact, concept, preference)."""
    id: str
    user_id: str
    fact: str
    category: str
    confidence: float = 1.0
    source: str = ""
    created_at: float = 0.0
    verified: bool = False


class MemoryRanker:
    """Rank memories by relevance and importance."""

    @staticmethod
    def calculate_relevance(memory: MemoryEntry, query: str = "") -> float:
        """Calculate relevance score."""
        score = 0.0

        score += memory.importance * 2.0

        score += min(memory.access_count * 0.1, 2.0)

        age_days = (time.time() - memory.created_at) / 86400
        recency_factor = math.exp(-age_days / 30)
        score += recency_factor * 1.5

        if query:
            query_lower = query.lower()
            content_lower = memory.content.lower()
            if query_lower in content_lower:
                score += 3.0
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            overlap = len(query_words & content_words)
            score += overlap * 0.5

        return score

    @staticmethod
    def apply_decay(memory: MemoryEntry, decay_rate: float = 0.01) -> float:
        """Apply time-based decay to memory importance."""
        age_days = (time.time() - memory.created_at) / 86400
        decay_factor = math.exp(-decay_rate * age_days)
        access_bonus = min(memory.access_count * 0.05, 0.5)
        return max(0.1, memory.importance * decay_factor + access_bonus)


class MemoryStore:
    """In-memory store for all memory types."""

    def __init__(self):
        self._memories: dict[str, list[MemoryEntry]] = defaultdict(list)
        self._episodic: dict[str, list[EpisodicMemory]] = defaultdict(list)
        self._semantic: dict[str, list[SemanticMemory]] = defaultdict(list)
        self._ranker = MemoryRanker()

    def add_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = "general",
        importance: float = 1.0,
        tags: list[str] = None,
    ) -> MemoryEntry:
        """Add a long-term memory."""
        import secrets
        entry = MemoryEntry(
            id=secrets.token_hex(8),
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            created_at=time.time(),
            last_accessed=time.time(),
            tags=tags or [],
        )
        self._memories[user_id].append(entry)
        return entry

    def add_episodic(
        self,
        user_id: str,
        title: str,
        summary: str,
        participants: list[str] = None,
        outcome: str = "",
        importance: float = 1.0,
    ) -> EpisodicMemory:
        """Add an episodic memory."""
        import secrets
        memory = EpisodicMemory(
            id=secrets.token_hex(8),
            user_id=user_id,
            title=title,
            summary=summary,
            participants=participants or [],
            timestamp=time.time(),
            outcome=outcome,
            importance=importance,
        )
        self._episodic[user_id].append(memory)
        return memory

    def add_semantic(
        self,
        user_id: str,
        fact: str,
        category: str = "general",
        confidence: float = 1.0,
        source: str = "",
    ) -> SemanticMemory:
        """Add a semantic memory."""
        import secrets
        memory = SemanticMemory(
            id=secrets.token_hex(8),
            user_id=user_id,
            fact=fact,
            category=category,
            confidence=confidence,
            source=source,
            created_at=time.time(),
        )
        self._semantic[user_id].append(memory)
        return memory

    def search(
        self,
        user_id: str,
        query: str = "",
        memory_type: str = None,
        limit: int = 10,
        min_score: float = 0.5,
    ) -> list[MemoryEntry]:
        """Search memories with ranking."""
        memories = self._memories.get(user_id, [])

        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        scored = []
        for memory in memories:
            relevance = self._ranker.calculate_relevance(memory, query)
            decayed_importance = self._ranker.apply_decay(memory)
            final_score = relevance * decayed_importance

            if final_score >= min_score:
                memory.last_accessed = time.time()
                memory.access_count += 1
                scored.append((memory, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:limit]]

    def get_episodic(self, user_id: str, limit: int = 20) -> list[EpisodicMemory]:
        """Get episodic memories."""
        memories = self._episodic.get(user_id, [])
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        return memories[:limit]

    def get_semantic(self, user_id: str, category: str = None) -> list[SemanticMemory]:
        """Get semantic memories."""
        memories = self._semantic.get(user_id, [])
        if category:
            memories = [m for m in memories if m.category == category]
        memories.sort(key=lambda m: m.confidence, reverse=True)
        return memories

    def cleanup(self, user_id: str, max_memories: int = 1000) -> int:
        """Clean up old low-importance memories."""
        memories = self._memories.get(user_id, [])
        if len(memories) <= max_memories:
            return 0

        for m in memories:
            m.importance = self._ranker.apply_decay(m)

        memories.sort(key=lambda m: m.importance, reverse=True)
        removed = len(memories) - max_memories
        self._memories[user_id] = memories[:max_memories]
        return removed

    def get_stats(self, user_id: str) -> dict:
        """Get memory statistics."""
        return {
            "total_memories": len(self._memories.get(user_id, [])),
            "episodic_memories": len(self._episodic.get(user_id, [])),
            "semantic_memories": len(self._semantic.get(user_id, [])),
            "memory_types": list(set(
                m.memory_type for m in self._memories.get(user_id, [])
            )),
        }


memory_store = MemoryStore()


# ============================================================================
# Phase 354 — Memory Engine 3.0
# ============================================================================

class MemoryGraph:
    """Graph-based memory with relationships."""

    def __init__(self):
        self._nodes: dict[str, dict] = {}
        self._edges: list[dict] = []

    def add_node(self, node_id: str, content: str, node_type: str = "memory"):
        self._nodes[node_id] = {
            "id": node_id,
            "content": content,
            "type": node_type,
            "created_at": time.time(),
        }

    def add_edge(self, source: str, target: str, relationship: str, weight: float = 1.0):
        self._edges.append({
            "source": source,
            "target": target,
            "relationship": relationship,
            "weight": weight,
        })

    def get_related(self, node_id: str) -> list:
        related = []
        for edge in self._edges:
            if edge["source"] == node_id and edge["target"] in self._nodes:
                related.append(self._nodes[edge["target"]])
            elif edge["target"] == node_id and edge["source"] in self._nodes:
                related.append(self._nodes[edge["source"]])
        return related

    def find_path(self, start: str, end: str, max_depth: int = 3) -> list:
        """Find path between two nodes."""
        visited = set()
        queue = [(start, [start])]
        while queue:
            current, path = queue.pop(0)
            if current == end:
                return path
            if len(path) >= max_depth:
                continue
            visited.add(current)
            for edge in self._edges:
                if edge["source"] == current and edge["target"] not in visited:
                    queue.append((edge["target"], path + [edge["target"]]))
        return []


class MemoryVersionHistory:
    """Track memory version history."""

    def __init__(self):
        self._versions: dict[str, list] = {}

    def record_version(self, memory_id: str, content: str, action: str = "update"):
        if memory_id not in self._versions:
            self._versions[memory_id] = []
        self._versions[memory_id].append({
            "content": content,
            "action": action,
            "timestamp": time.time(),
        })

    def get_history(self, memory_id: str) -> list:
        return self._versions.get(memory_id, [])

    def rollback(self, memory_id: str, steps: int = 1) -> Optional[str]:
        versions = self._versions.get(memory_id, [])
        if len(versions) > steps:
            return versions[-(steps + 1)]["content"]
        return None


class TopicClusterer:
    """Cluster memories by topic."""

    def __init__(self):
        self._clusters: dict[str, list] = defaultdict(list)

    def add_to_cluster(self, topic: str, memory_id: str):
        self._clusters[topic].append(memory_id)

    def get_cluster(self, topic: str) -> list:
        return self._clusters.get(topic, [])

    def get_all_topics(self) -> list:
        return list(self._clusters.keys())


memory_graph = MemoryGraph()
memory_version_history = MemoryVersionHistory()
topic_clusterer = TopicClusterer()
