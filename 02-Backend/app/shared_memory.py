"""Shared Memory System for Multi-Agent Collaboration.

Agents can share context, long-term memory, and knowledge through
a unified memory interface with semantic search and expiration.
"""

import time
import logging
import hashlib
import json
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    user_id: str
    agent_id: str = ""
    importance: float = 1.0
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    access_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class SharedContext:
    """Shared context for a collaboration session."""
    session_id: str
    data: dict = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)


class MemoryStore:
    """In-memory storage with semantic search capabilities."""

    def __init__(self):
        self._memories: dict[str, MemoryEntry] = {}
        self._user_index: dict[str, set[str]] = defaultdict(set)
        self._tag_index: dict[str, set[str]] = defaultdict(set)

    def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry."""
        self._memories[entry.id] = entry
        self._user_index[entry.user_id].add(entry.id)
        for tag in entry.tags:
            self._tag_index[tag].add(entry.id)
        return entry.id

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a memory by ID."""
        entry = self._memories.get(memory_id)
        if entry:
            entry.access_count += 1
        return entry

    def search(self, query: str, user_id: str = None, limit: int = 10) -> list[MemoryEntry]:
        """Search memories by keyword matching."""
        results = []
        query_lower = query.lower()

        for entry in self._memories.values():
            if user_id and entry.user_id != user_id:
                continue
            if entry.expires_at and time.time() > entry.expires_at:
                continue
            if query_lower in entry.content.lower():
                results.append(entry)

        results.sort(key=lambda e: e.importance * e.access_count, reverse=True)
        return results[:limit]

    def get_by_user(self, user_id: str) -> list[MemoryEntry]:
        """Get all memories for a user."""
        ids = self._user_index.get(user_id, set())
        return [self._memories[mid] for mid in ids if mid in self._memories]

    def get_by_tag(self, tag: str) -> list[MemoryEntry]:
        """Get memories by tag."""
        ids = self._tag_index.get(tag, set())
        return [self._memories[mid] for mid in ids if mid in self._memories]

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        entry = self._memories.pop(memory_id, None)
        if entry:
            self._user_index[entry.user_id].discard(memory_id)
            for tag in entry.tags:
                self._tag_index[tag].discard(memory_id)
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired memories."""
        now = time.time()
        expired = [mid for mid, e in self._memories.items() if e.expires_at and now > e.expires_at]
        for mid in expired:
            self.delete(mid)
        return len(expired)


class SharedMemoryManager:
    """Manage shared memory across agents and sessions."""

    def __init__(self):
        self._store = MemoryStore()
        self._contexts: dict[str, SharedContext] = {}

    def create_memory(
        self,
        content: str,
        user_id: str,
        agent_id: str = "",
        importance: float = 1.0,
        tags: list[str] = None,
        ttl_seconds: int = 0,
    ) -> MemoryEntry:
        """Create a new memory entry."""
        import secrets
        entry = MemoryEntry(
            id=secrets.token_hex(8),
            content=content,
            user_id=user_id,
            agent_id=agent_id,
            importance=importance,
            tags=tags or [],
            expires_at=time.time() + ttl_seconds if ttl_seconds > 0 else 0,
        )
        self._store.store(entry)
        return entry

    def recall(self, query: str, user_id: str = None, limit: int = 10) -> list[MemoryEntry]:
        """Recall memories matching a query."""
        return self._store.search(query, user_id, limit)

    def forget(self, memory_id: str) -> bool:
        """Remove a memory."""
        return self._store.delete(memory_id)

    def set_context(self, session_id: str, key: str, value: Any):
        """Set shared context for a session."""
        if session_id not in self._contexts:
            self._contexts[session_id] = SharedContext(session_id=session_id)
        self._contexts[session_id].data[key] = value
        self._contexts[session_id].updated_at = time.time()

    def get_context(self, session_id: str, key: str = None) -> Any:
        """Get shared context."""
        ctx = self._contexts.get(session_id)
        if not ctx:
            return None
        if key:
            return ctx.data.get(key)
        return ctx.data

    def compress_memories(self, user_id: str) -> dict:
        """Compress and summarize memories for a user."""
        memories = self._store.get_by_user(user_id)
        if not memories:
            return {"compressed": False, "reason": "No memories"}

        return {
            "compressed": True,
            "total_memories": len(memories),
            "total_size": sum(len(m.content) for m in memories),
            "top_tags": list(set(tag for m in memories for tag in m.tags))[:10],
        }

    def get_stats(self, user_id: str) -> dict:
        """Get memory statistics."""
        memories = self._store.get_by_user(user_id)
        return {
            "total": len(memories),
            "total_size": sum(len(m.content) for m in memories),
            "avg_importance": sum(m.importance for m in memories) / max(len(memories), 1),
        }


shared_memory = SharedMemoryManager()
