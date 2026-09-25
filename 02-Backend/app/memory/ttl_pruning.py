"""Memory TTL and pruning policies."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum


class PruningStrategy(Enum):
    TTL = "ttl"
    LRU = "lru"
    LFU = "lfu"
    IMPORTANCE = "importance"
    HYBRID = "hybrid"


@dataclass
class TTLPolicy:
    memory_type: str
    ttl_seconds: int
    strategy: PruningStrategy = PruningStrategy.TTL
    max_items: int = 10000
    importance_threshold: float = 0.1


class MemoryPruner:
    _policies: Dict[str, TTLPolicy] = {}
    _last_pruned: Dict[str, datetime] = {}

    @classmethod
    def register_policy(cls, policy: TTLPolicy) -> None:
        cls._policies[policy.memory_type] = policy

    @classmethod
    def should_prune(cls, memory_type: str, created_at: datetime, importance: float = 0.5) -> bool:
        policy = cls._policies.get(memory_type)
        if not policy:
            return False
        age = (datetime.now(timezone.utc) - created_at).total_seconds()
        if policy.strategy == PruningStrategy.TTL:
            return age > policy.ttl_seconds
        elif policy.strategy == PruningStrategy.IMPORTANCE:
            return importance < policy.importance_threshold
        return age > policy.ttl_seconds

    @classmethod
    def get_policy(cls, memory_type: str) -> Optional[TTLPolicy]:
        return cls._policies.get(memory_type)

    @classmethod
    def list_expired(cls, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        expired = []
        for memory in memories:
            created_at = memory.get("created_at", datetime.now(timezone.utc))
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            memory_type = memory.get("type", "default")
            importance = memory.get("importance", 0.5)
            if cls.should_prune(memory_type, created_at, importance):
                expired.append(memory)
        return expired
