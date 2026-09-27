"""Memory service for long-term conversation memory."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .vector_store import VectorStore
from .models import MemoryCreate, MemoryResponse, MemorySearch, MemorySummary

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self) -> None:
        self._store = VectorStore()

    def create_memory(self, body: MemoryCreate) -> MemoryResponse:
        record = self._store.add_memory(
            user_id=body.user_id,
            content=body.content,
            metadata=body.metadata,
        )
        return MemoryResponse(
            id=record.id,
            content=record.content,
            conversation_id=body.conversation_id,
            user_id=body.user_id,
            importance=body.importance,
            created_at=record.created_at,
        )

    def search_memories(self, body: MemorySearch) -> list[tuple[MemoryResponse, float]]:
        results = self._store.search(
            user_id="user",
            query=body.query,
            limit=body.limit,
            min_similarity=body.min_similarity,
        )
        return [
            (
                MemoryResponse(
                    id=r.id,
                    content=r.content,
                    conversation_id=r.metadata.get("conversation_id"),
                    user_id="user",
                    importance=r.metadata.get("importance", 0.5),
                    created_at=r.created_at,
                ),
                score,
            )
            for r, score in results
        ]

    def get_summary(self, user_id: str) -> MemorySummary:
        memories = self._store.get_memories(user_id)
        conversations = {m.metadata.get("conversation_id") for m in memories if m.metadata.get("conversation_id")}
        avg_importance = sum(m.metadata.get("importance", 0.5) for m in memories) / len(memories) if memories else 0.0
        return MemorySummary(
            total_memories=len(memories),
            total_conversations=len(conversations),
            avg_importance=avg_importance,
            recent_memories=[],
        )

    def delete_memory(self, memory_id: str) -> bool:
        return self._store.delete_memory(memory_id)
