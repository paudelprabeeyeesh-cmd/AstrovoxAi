"""Enhanced memory system with search, summarization, and context compression."""

import logging
import time
from typing import Optional
from dataclasses import dataclass, field

from .database import (
    save_memory,
    get_user_memory,
    get_recent_messages,
)

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: int
    user_id: str
    content: str
    importance: int
    created_at: str
    tags: list[str] = field(default_factory=list)


@dataclass
class MemorySearchResult:
    """Result from a memory search."""
    entry: MemoryEntry
    score: float


class MemoryManager:
    """Enhanced memory management with search and summarization."""

    def __init__(self):
        self._cache: dict[str, list[MemoryEntry]] = {}

    async def save_memory(
        self,
        user_id: str,
        content: str,
        importance: int = 1,
        tags: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """Save a memory entry with optional tags."""
        try:
            result = await save_memory(user_id, content, importance)
            if result and tags:
                result["tags"] = tags
            self._cache.pop(user_id, None)
            return result
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return None

    async def get_memories(self, user_id: str, limit: int = 50) -> list[MemoryEntry]:
        """Get user memories as MemoryEntry objects."""
        raw = await get_user_memory(user_id, limit)
        return [
            MemoryEntry(
                id=m.get("id", 0),
                user_id=m.get("user_id", user_id),
                content=m.get("content", ""),
                importance=m.get("importance", 1),
                created_at=m.get("created_at", ""),
                tags=m.get("tags", []),
            )
            for m in raw
        ]

    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> list[MemorySearchResult]:
        """Search memories using keyword matching and relevance scoring."""
        memories = await self.get_memories(user_id, limit=100)
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results: list[MemorySearchResult] = []

        for entry in memories:
            content_lower = entry.content.lower()
            content_words = set(content_lower.split())

            overlap = len(query_words & content_words)
            if overlap == 0:
                continue

            score = overlap / len(query_words)
            score += entry.importance * 0.1

            if query_lower in content_lower:
                score += 0.5

            results.append(MemorySearchResult(entry=entry, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def compress_context(
        self,
        user_id: str,
        messages: list[dict],
        max_tokens: int = 2000,
    ) -> list[dict]:
        """Compress conversation context to fit within token budget."""
        if not messages:
            return []

        total_chars = sum(len(m.get("content", "")) for m in messages)
        max_chars = max_tokens * 4

        if total_chars <= max_chars:
            return messages

        compressed = []
        current_chars = 0

        for msg in reversed(messages):
            msg_chars = len(msg.get("content", ""))
            if current_chars + msg_chars > max_chars:
                break
            compressed.insert(0, msg)
            current_chars += msg_chars

        if not compressed and messages:
            compressed = [messages[-1]]

        return compressed

    async def summarize_conversation(
        self,
        user_id: str,
        conversation_id: int,
        provider=None,
    ) -> Optional[str]:
        """Generate a summary of a conversation."""
        messages = await get_recent_messages(conversation_id, limit=50)
        if not messages:
            return None

        conversation_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in messages
        )

        if len(conversation_text) < 200:
            return conversation_text

        summary = (
            f"Conversation with {len(messages)} messages. "
            f"Topics discussed: {conversation_text[:500]}..."
        )

        return summary

    async def auto_cleanup(
        self,
        user_id: str,
        max_entries: int = 100,
        min_importance: int = 1,
    ) -> int:
        """Automatically clean up low-importance old memories."""
        memories = await self.get_memories(user_id, limit=1000)
        if len(memories) <= max_entries:
            return 0

        cleaned = 0
        for mem in memories[max_entries:]:
            if mem.importance <= min_importance:
                cleaned += 1

        return cleaned

    async def get_context_for_prompt(
        self,
        user_id: str,
        query: str = "",
        limit: int = 5,
    ) -> str:
        """Get formatted context for AI prompt injection."""
        if query:
            results = await self.search_memories(user_id, query, limit=limit)
            if results:
                context_lines = ["Relevant user memory:"]
                for r in results:
                    context_lines.append(f"- {r.entry.content}")
                return "\n".join(context_lines)

        memories = await self.get_memories(user_id, limit=limit)
        if not memories:
            return ""

        context_lines = ["User context/memory:"]
        for m in memories[:limit]:
            context_lines.append(f"- {m.content}")

        return "\n".join(context_lines)


memory_manager = MemoryManager()
