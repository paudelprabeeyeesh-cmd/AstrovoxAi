"""Long-term memory with persistence."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json


class MemoryImportance(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    ARCHIVAL = 1


@dataclass
class LongTermMemory:
    memory_id: str
    user_id: str
    content: str
    importance: MemoryImportance = MemoryImportance.MEDIUM
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0


class LongTermMemoryStore:
    _memories: Dict[str, LongTermMemory] = {}

    @classmethod
    def store(cls, user_id: str, content: str, importance: MemoryImportance = MemoryImportance.MEDIUM, tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> LongTermMemory:
        memory_id = f"ltm_{user_id}_{len(cls._memories)}"
        memory = LongTermMemory(
            memory_id=memory_id,
            user_id=user_id,
            content=content,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {},
        )
        cls._memories[memory_id] = memory
        return memory

    @classmethod
    def get(cls, memory_id: str) -> Optional[LongTermMemory]:
        memory = cls._memories.get(memory_id)
        if memory:
            memory.accessed_at = datetime.now(timezone.utc)
            memory.access_count += 1
        return memory

    @classmethod
    def search(cls, user_id: str, query: str, limit: int = 10) -> List[LongTermMemory]:
        results = []
        query_lower = query.lower()
        for memory in cls._memories.values():
            if memory.user_id == user_id and (query_lower in memory.content.lower() or any(query_lower in tag.lower() for tag in memory.tags)):
                results.append(memory)
        results.sort(key=lambda m: (m.importance.value, m.accessed_at), reverse=True)
        return results[:limit]
