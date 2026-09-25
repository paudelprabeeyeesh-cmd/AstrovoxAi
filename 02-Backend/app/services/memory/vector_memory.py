"""Vector memory with embedding storage."""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np
import uuid


@dataclass
class VectorMemory:
    vector_id: str
    user_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class VectorMemoryStore:
    _vectors: Dict[str, VectorMemory] = {}
    _user_index: Dict[str, List[str]] = {}

    @classmethod
    def add(cls, user_id: str, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None) -> VectorMemory:
        vector_id = str(uuid.uuid4())
        vm = VectorMemory(
            vector_id=vector_id,
            user_id=user_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
        )
        cls._vectors[vector_id] = vm
        if user_id not in cls._user_index:
            cls._user_index[user_id] = []
        cls._user_index[user_id].append(vector_id)
        return vm

    @classmethod
    def search(cls, user_id: str, query_embedding: List[float], top_k: int = 10, threshold: float = 0.7) -> List[Tuple[VectorMemory, float]]:
        user_vectors = cls._user_index.get(user_id, [])
        results = []
        for vid in user_vectors:
            vm = cls._vectors.get(vid)
            if vm:
                similarity = cls._cosine_similarity(query_embedding, vm.embedding)
                if similarity >= threshold:
                    results.append((vm, similarity))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    @classmethod
    def delete(cls, vector_id: str) -> None:
        vm = cls._vectors.pop(vector_id, None)
        if vm and vm.user_id in cls._user_index:
            cls._user_index[vm.user_id].remove(vector_id)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        a_np, b_np = np.array(a), np.array(b)
        return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))
