"""Memory management for high-performance runtime."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryPool:
    pool_id: str
    size_bytes: int
    used_bytes: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryManager:
    def __init__(self) -> None:
        self._pools: Dict[str, MemoryPool] = {}

    def create_pool(self, pool_id: str, size_bytes: int) -> MemoryPool:
        pool = MemoryPool(pool_id=pool_id, size_bytes=size_bytes)
        self._pools[pool_id] = pool
        return pool

    def allocate(self, pool_id: str, size_bytes: int) -> bool:
        pool = self._pools.get(pool_id)
        if not pool or pool.used_bytes + size_bytes > pool.size_bytes:
            return False
        pool.used_bytes += size_bytes
        return True

    def get_pool(self, pool_id: str) -> Optional[MemoryPool]:
        return self._pools.get(pool_id)


memory_manager = MemoryManager()
