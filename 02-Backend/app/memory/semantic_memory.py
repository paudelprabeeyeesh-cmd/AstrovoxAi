"""Semantic memory with vector embeddings."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np


@dataclass
class SemanticMemoryItem:
    memory_id: str
    user_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SemanticMemory:
    _memories: Dict[str, SemanticMemoryItem] = {}
    _user_index: Dict[str, List[str]] = {}

    @classmethod
    def store(cls, user_id: str, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None) -> SemanticMemoryItem:
        memory_id = f"mem_{user_id}_{len(cls._memories)}"
        item = SemanticMemoryItem(
            memory_id=memory_id,
            user_id=user_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
        )
        cls._memories[memory_id] = item
        if user_id not in cls._user_index:
            cls._user_index[user_id] = []
        cls._user_index[user_id].append(memory_id)
        return item

    @classmethod
    def retrieve(cls, memory_id: str) -> Optional[SemanticMemoryItem]:
        item = cls._memories.get(memory_id)
        if item:
            item.last_accessed = datetime.now(timezone.utc)
        return item

    @classmethod
    def search_by_similarity(cls, user_id: str, query_embedding: List[float], top_k: int = 5) -> List[SemanticMemoryItem]:
        user_memories = cls._user_index.get(user_id, [])
        scored = []
        for memory_id in user_memories:
            item = cls._memories.get(memory_id)
            if item:
                score = cls._cosine_similarity(query_embedding, item.embedding)
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        a_np, b_np = np.array(a), np.array(b)
        return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))
