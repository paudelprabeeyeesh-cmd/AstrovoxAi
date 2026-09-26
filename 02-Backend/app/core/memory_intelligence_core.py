"""
Memory intelligence with semantic search and importance scoring.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    memory_id: str
    content: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


class MemoryIntelligence:
    """Intelligent memory management with semantic search."""

    def __init__(self, max_memories: int = 10000):
        self.memories: Dict[str, MemoryEntry] = {}
        self.max_memories = max_memories
        self.embedding_engine = None
        self._search_cache: Dict[str, Tuple[List[MemoryEntry], float]] = {}
        self._SEARCH_TTL = 30.0

    def add_memory(self, content: str, embedding: Optional[np.ndarray] = None, metadata: Optional[Dict[str, Any]] = None, importance: float = 0.5) -> str:
        if len(self.memories) >= self.max_memories:
            self._evict_low_importance()
        memory_id = str(__import__("uuid").uuid4())
        entry = MemoryEntry(memory_id=memory_id, content=content, embedding=embedding, metadata=metadata or {}, importance=importance)
        self.memories[memory_id] = entry
        return memory_id

    def search(self, query_embedding: np.ndarray, top_k: int = 10, min_similarity: float = 0.0) -> List[MemoryEntry]:
        cache_key = f"{query_embedding.tobytes()}:{top_k}:{min_similarity}"
        now = time.time()
        cached = self._search_cache.get(cache_key)
        if cached and (now - cached[1]) < self._SEARCH_TTL:
            return list(cached[0])
        results = []
        query_norm = np.linalg.norm(query_embedding) + 1e-8
        for entry in self.memories.values():
            if entry.embedding is None:
                continue
            sim = float(np.dot(query_embedding, entry.embedding) / (query_norm * (np.linalg.norm(entry.embedding) + 1e-8)))
            if sim >= min_similarity:
                results.append((sim, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        result = [entry for _, entry in results[:top_k]]
        self._search_cache[cache_key] = (result, now)
        return result

    def search_by_text(self, query_text: str, top_k: int = 5) -> List[MemoryEntry]:
        if self.embedding_engine is None:
            try:
                from app.core.embeddings_core import EmbeddingEngine
                self.embedding_engine = EmbeddingEngine()
            except Exception:
                return []
        query_emb = self.embedding_engine.embed_query(query_text)
        return self.search(query_emb, top_k=top_k)

    def get_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        entry = self.memories.get(memory_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = datetime.now()
        return entry

    def update_importance(self, memory_id: str, importance: float):
        entry = self.memories.get(memory_id)
        if entry:
            entry.importance = importance

    def delete_memory(self, memory_id: str) -> bool:
        return self.memories.pop(memory_id, None) is not None

    def _evict_low_importance(self):
        if not self.memories:
            return
        sorted_memories = sorted(self.memories.values(), key=lambda m: m.importance)
        to_remove = min(100, len(sorted_memories))
        for entry in sorted_memories[:to_remove]:
            del self.memories[entry.memory_id]

    def get_stats(self) -> dict:
        return {
            "total_memories": len(self.memories),
            "max_memories": self.max_memories,
            "avg_importance": round(sum(m.importance for m in self.memories.values()) / max(len(self.memories), 1), 3),
        }
