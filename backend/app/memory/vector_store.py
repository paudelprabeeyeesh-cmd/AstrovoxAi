"""In-memory vector store for conversation memory."""
from __future__ import annotations

import hashlib
import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryRecord:
    id: str
    content: str
    embedding: list[float]
    metadata: dict
    created_at: datetime


class VectorStore:
    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension
        self._records: dict[str, MemoryRecord] = {}
        self._user_index: dict[str, list[str]] = {}

    def _hash_id(self, content: str, user_id: str) -> str:
        return hashlib.sha256(f"{user_id}:{content}".encode()).hexdigest()[:16]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def _mock_embed(self, text: str) -> list[float]:
        import random
        random.seed(hash(text) % (2**32))
        vec = [random.uniform(-1, 1) for _ in range(self._dimension)]
        magnitude = math.sqrt(sum(x * x for x in vec))
        return [x / magnitude for x in vec] if magnitude > 0 else vec

    def add_memory(self, user_id: str, content: str, metadata: dict | None = None, memory_id: str | None = None) -> MemoryRecord:
        memory_id = memory_id or self._hash_id(content, user_id)
        embedding = self._mock_embed(content)
        record = MemoryRecord(
            id=memory_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            created_at=datetime.now(),
        )
        self._records[memory_id] = record
        self._user_index.setdefault(user_id, []).append(memory_id)
        return record

    def search(self, user_id: str, query: str, limit: int = 10, min_similarity: float = 0.7) -> list[tuple[MemoryRecord, float]]:
        query_embedding = self._mock_embed(query)
        results = []
        for memory_id in self._user_index.get(user_id, []):
            record = self._records.get(memory_id)
            if not record:
                continue
            similarity = self._cosine_similarity(query_embedding, record.embedding)
            if similarity >= min_similarity:
                results.append((record, similarity))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_memories(self, user_id: str, limit: int = 100) -> list[MemoryRecord]:
        return [self._records[mid] for mid in self._user_index.get(user_id, [])[-limit:]]

    def delete_memory(self, memory_id: str) -> bool:
        if memory_id in self._records:
            del self._records[memory_id]
            for user_id, memories in self._user_index.items():
                if memory_id in memories:
                    memories.remove(memory_id)
            return True
        return False

    def get_user_memory_count(self, user_id: str) -> int:
        return len(self._user_index.get(user_id, []))
