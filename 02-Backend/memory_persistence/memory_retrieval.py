"""
Memory Retrieval - Task 117

Ranks memories by recency and relevance using combined signals.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class Memory:
    memory_id: str
    content: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    category: str = "general"


class MemoryRetrieval:
    """
    Ranks memories by recency and relevance with combined signals.
    
    Scoring combines:
    - Semantic similarity (embedding-based)
    - Recency (time decay)
    - Importance
    - Access frequency
    """

    def __init__(
        self,
        recency_decay_hours: float = 24.0,
        similarity_weight: float = 0.4,
        recency_weight: float = 0.2,
        importance_weight: float = 0.25,
        access_weight: float = 0.15,
    ):
        self.recency_decay_hours = recency_decay_hours
        self.similarity_weight = similarity_weight
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.access_weight = access_weight
        self._memories: Dict[str, Memory] = {}

    def add_memory(self, memory: Memory) -> str:
        """Add a memory to the store."""
        self._memories[memory.memory_id] = memory
        return memory.memory_id

    def add_memories(self, memories: List[Memory]) -> List[str]:
        """Add multiple memories."""
        return [self.add_memory(m) for m in memories]

    def _recency_score(self, created_at: datetime, now: datetime) -> float:
        """Compute recency score with exponential decay."""
        age_hours = (now - created_at).total_seconds() / 3600.0
        decay = math.exp(-age_hours / self.recency_decay_hours)
        return decay

    def _access_score(self, access_count: int, now: datetime, last_accessed: datetime) -> float:
        """Compute access frequency score."""
        freq_score = min(math.log(access_count + 1) / 5.0, 1.0)
        recency_access = self._recency_score(last_accessed, now)
        return 0.5 * freq_score + 0.5 * recency_access

    def _compute_similarity(
        self,
        query_embedding: Optional[np.ndarray],
        memory_embedding: Optional[np.ndarray],
    ) -> float:
        """Compute cosine similarity between query and memory embeddings."""
        if query_embedding is None or memory_embedding is None:
            return 0.0
        norm_q = np.linalg.norm(query_embedding)
        norm_m = np.linalg.norm(memory_embedding)
        if norm_q == 0 or norm_m == 0:
            return 0.0
        return float(np.dot(query_embedding, memory_embedding) / (norm_q * norm_m))

    def retrieve(
        self,
        query_embedding: Optional[np.ndarray] = None,
        query_text: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.0,
        category_filter: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> List[Tuple[Memory, float]]:
        """
        Retrieve and rank memories by combined signals.
        
        Args:
            query_embedding: Embedding vector for semantic search
            query_text: Optional text query (for BM25-like matching)
            top_k: Maximum number of results
            min_score: Minimum combined score threshold
            category_filter: Optional category to filter by
            now: Current time (for testing)
        
        Returns:
            List of (Memory, score) tuples sorted by score descending
        """
        if now is None:
            now = datetime.utcnow()
        
        results = []
        for memory in self._memories.values():
            if category_filter and memory.category != category_filter:
                continue
            
            similarity = self._compute_similarity(query_embedding, memory.embedding)
            recency = self._recency_score(memory.created_at, now)
            importance = memory.importance
            access = self._access_score(memory.access_count, now, memory.last_accessed)
            
            combined_score = (
                self.similarity_weight * similarity
                + self.recency_weight * recency
                + self.importance_weight * importance
                + self.access_weight * access
            )
            
            if combined_score >= min_score:
                results.append((memory, combined_score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """Get memory by ID and update access tracking."""
        memory = self._memories.get(memory_id)
        if memory:
            memory.access_count += 1
            memory.last_accessed = datetime.utcnow()
        return memory

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        return self._memories.pop(memory_id, None) is not None

    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        now = datetime.utcnow()
        scores = []
        for m in self._memories.values():
            scores.append(self._recency_score(m.created_at, now))
        
        return {
            "total_memories": len(self._memories),
            "avg_recency": float(np.mean(scores)) if scores else 0.0,
            "avg_importance": float(np.mean([m.importance for m in self._memories.values()])) if self._memories else 0.0,
        }
