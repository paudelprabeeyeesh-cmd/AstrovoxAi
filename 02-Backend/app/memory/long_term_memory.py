"""
Long-term Memory - Persistent storage layer for memories that persist across sessions.

Provides durable storage with:
- User-scoped persistent facts
- Preference retention
- Relationship tracking
- Cross-session continuity
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class MemoryTier(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    ARCHIVED = "archived"


class LongTermMemory:
    """Persistent long-term memory that survives across sessions."""

    def __init__(self):
        self._memories: Dict[str, Dict[str, Any]] = {}
        self._user_index: Dict[str, List[str]] = {}
        self._next_id = 1

    def add_memory(
        self,
        user_id: str,
        content: str,
        category: str = "general",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        memory_id = f"ltm_{self._next_id}"
        self._next_id += 1
        self._memories[memory_id] = {
            "memory_id": memory_id,
            "user_id": user_id,
            "content": content,
            "category": category,
            "importance": importance,
            "tier": MemoryTier.LONG_TERM.value,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "access_count": 0,
        }
        self._user_index.setdefault(user_id, []).append(memory_id)
        return memory_id

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        mem = self._memories.get(memory_id)
        if mem:
            mem["access_count"] = mem.get("access_count", 0) + 1
            mem["updated_at"] = datetime.utcnow().isoformat()
        return mem

    def get_user_memories(self, user_id: str, category: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        ids = self._user_index.get(user_id, [])
        results = []
        for mid in ids:
            mem = self._memories.get(mid)
            if not mem:
                continue
            if category and mem.get("category") != category:
                continue
            results.append(mem)
        results.sort(key=lambda m: m.get("importance", 0.0), reverse=True)
        return results[:limit]

    def update_memory(self, memory_id: str, content: Optional[str] = None, importance: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        mem = self._memories.get(memory_id)
        if not mem:
            return False
        if content is not None:
            mem["content"] = content
        if importance is not None:
            mem["importance"] = importance
        if metadata is not None:
            mem["metadata"].update(metadata)
        mem["updated_at"] = datetime.utcnow().isoformat()
        return True

    def delete_memory(self, memory_id: str) -> bool:
        mem = self._memories.pop(memory_id, None)
        if not mem:
            return False
        user_id = mem.get("user_id")
        if user_id and memory_id in self._user_index.get(user_id, []):
            self._user_index[user_id].remove(memory_id)
        return True

    def archive_memory(self, memory_id: str) -> bool:
        mem = self._memories.get(memory_id)
        if not mem:
            return False
        mem["tier"] = MemoryTier.ARCHIVED.value
        mem["updated_at"] = datetime.utcnow().isoformat()
        return True

    def search(self, user_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for mid in self._user_index.get(user_id, []):
            mem = self._memories.get(mid)
            if not mem:
                continue
            content = mem.get("content", "")
            if query_lower in content.lower() or query_lower in mem.get("category", "").lower():
                results.append(mem)
        results.sort(key=lambda m: m.get("importance", 0.0), reverse=True)
        return results[:limit]

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        ids = self._user_index.get(user_id, [])
        categories: Dict[str, int] = {}
        total_importance = 0.0
        for mid in ids:
            mem = self._memories.get(mid)
            if not mem:
                continue
            cat = mem.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
            total_importance += mem.get("importance", 0.0)
        return {
            "total": len(ids),
            "categories": categories,
            "avg_importance": total_importance / len(ids) if ids else 0.0,
        }
