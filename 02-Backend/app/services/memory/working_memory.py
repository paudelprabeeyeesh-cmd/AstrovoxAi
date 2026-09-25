"""Working memory for active context."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta


@dataclass
class MemoryItem:
    key: str
    value: Any
    priority: int = 50
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    _memory: Dict[str, MemoryItem] = {}
    _max_items = 1000

    @classmethod
    def put(cls, key: str, value: Any, priority: int = 50, expires_in: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        item = MemoryItem(
            key=key,
            value=value,
            priority=priority,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        cls._memory[key] = item
        cls._evict_if_needed()

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        item = cls._memory.get(key)
        if not item:
            return None
        if item.expires_at and item.expires_at < datetime.now(timezone.utc):
            del cls._memory[key]
            return None
        return item.value

    @classmethod
    def delete(cls, key: str) -> None:
        cls._memory.pop(key, None)

    @classmethod
    def clear(cls) -> None:
        cls._memory.clear()

    @classmethod
    def list_keys(cls) -> List[str]:
        now = datetime.now(timezone.utc)
        return [k for k, v in cls._memory.items() if not v.expires_at or v.expires_at > now]

    @classmethod
    def _evict_if_needed(cls) -> None:
        if len(cls._memory) <= cls._max_items:
            return
        sorted_items = sorted(cls._memory.items(), key=lambda x: x[1].priority)
        for key, _ in sorted_items[: len(cls._memory) - cls._max_items]:
            del cls._memory[key]
