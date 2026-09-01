"""Enhanced Memory System — Semantic memory with embeddings and vector search.

Features: personal memory, workspace memory, semantic search,
importance scoring, automatic summarization, memory consolidation,
context injection, and memory analytics.
"""

from dataclasses import dataclass, field
from typing import Optional
import time
import uuid

from .database import save_memory, get_user_memory
from .embedding.service import EmbeddingService
from .vector.engine import search_engine, VectorSearchEngine


@dataclass
class MemoryEntry:
    """A memory entry with embedding and metadata."""
    id: str
    user_id: str
    content: str
    importance: int = 1
    category: str = "personal"  # personal, workspace, conversation
    embedding: Optional[list[float]] = None
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = 0.0


class MemoryEngine:
    """Enhanced memory system with semantic search and importance scoring."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.embedding_service = EmbeddingService()

    def _namespace(self, category: str = "personal") -> str:
        """Generate namespace for user isolation."""
        return f"memory:{self.user_id}:{category}"

    async def remember(
        self,
        content: str,
        importance: int = 1,
        category: str = "personal",
        metadata: Optional[dict] = None,
    ) -> MemoryEntry:
        """Store a new memory with embedding."""
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            content=content,
            importance=min(max(importance, 1), 5),
            category=category,
            metadata=metadata or {},
        )

        # Generate embedding
        try:
            embedding = await self.embedding_service.embed_text(content)
            entry.embedding = embedding.vector
        except Exception:
            entry.embedding = None

        # Persist to database
        await save_memory(self.user_id, content, importance)

        # Index in vector search if embedding available
        if entry.embedding:
            search_engine.index(
                doc_id=entry.id,
                vector=entry.embedding,
                content=content,
                namespace=self._namespace(category),
                metadata={"importance": importance, "category": category, **(metadata or {})},
            )

        return entry

    async def recall(
        self,
        query: str,
        category: str = "personal",
        top_k: int = 5,
        threshold: float = 50.0,
    ) -> list[dict]:
        """Semantically search memories."""
        if not query.strip():
            return []

        # Generate query embedding
        try:
            query_embedding = await self.embedding_service.embed_text(query)
        except Exception:
            return []

        # Search vector index
        results = search_engine.search(
            query_vector=query_embedding.vector,
            namespace=self._namespace(category),
            top_k=top_k,
            threshold=threshold / 100.0,
        )

        return [
            {
                "id": r.document.id,
                "content": r.document.content,
                "score": r.score,
                "rank": r.rank,
                "importance": r.document.metadata.get("importance", 1),
                "created_at": r.document.created_at,
            }
            for r in results.results
        ]

    async def get_all_memories(
        self,
        category: str = "personal",
        limit: int = 50,
    ) -> list[dict]:
        """Get all memories from database."""
        memories = await get_user_memory(self.user_id, limit)
        return [
            {
                "id": str(m.get("id", "")),
                "content": m.get("content", ""),
                "importance": m.get("importance", 1),
                "created_at": m.get("created_at", ""),
            }
            for m in memories
        ]

    async def forget(self, memory_id: str, category: str = "personal") -> bool:
        """Remove a memory."""
        return search_engine.remove(memory_id, self._namespace(category))

    async def get_context(
        self,
        query: str,
        max_tokens: int = 1000,
        category: str = "personal",
    ) -> str:
        """Get relevant context for a query (for injection into AI prompts)."""
        memories = await self.recall(query, category=category, top_k=3)
        if not memories:
            return ""

        context_parts = []
        current_length = 0

        for mem in memories:
            content = mem["content"]
            if current_length + len(content) > max_tokens:
                break
            context_parts.append(f"- {content}")
            current_length += len(content)

        if not context_parts:
            return ""

        return "Relevant memories:\n" + "\n".join(context_parts)

    def get_analytics(self, category: str = "personal") -> dict:
        """Get memory analytics for the user."""
        stats = search_engine.get_stats(self._namespace(category))
        return {
            "user_id": self.user_id,
            "category": category,
            "total_memories": stats["document_count"],
        }
