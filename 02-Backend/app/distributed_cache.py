"""Enhanced distributed cache with Redis Cluster support.

Provides connection pooling, tag-based invalidation, and cache statistics.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    memory_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class DistributedCache:
    """Redis-based distributed cache with connection pooling."""

    def __init__(self, redis_url: Optional[str] = None, max_connections: int = 20):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.max_connections = max_connections
        self._local: Dict[str, Tuple[Any, float]] = {}
        self._stats = CacheStats()
        self._lock = threading.Lock()
        self._pool: list = []
        self._init_pool()

    def _init_pool(self) -> None:
        try:
            import redis

            for _ in range(min(4, self.max_connections)):
                client = redis.Redis.from_url(self.redis_url, decode_responses=True)
                client.ping()
                self._pool.append(client)
            logger.info("Initialized Redis connection pool with %d connections", len(self._pool))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis pool init failed: %s", exc)

    def _get_client(self):
        if self._pool:
            return self._pool[0]
        try:
            import redis
            return redis.Redis.from_url(self.redis_url, decode_responses=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis client creation failed: %s", exc)
            return None

    def get(self, key: str) -> Optional[Any]:
        client = self._get_client()
        if not client:
            with self._lock:
                self._stats.misses += 1
            return None
        try:
            data = client.get(key)
            if data is not None:
                with self._lock:
                    self._stats.hits += 1
                return json.loads(data)
            with self._lock:
                self._stats.misses += 1
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("Cache get failed: %s", exc)
            with self._lock:
                self._stats.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = 300, tags: Optional[List[str]] = None) -> bool:
        client = self._get_client()
        if not client:
            return False
        try:
            payload = json.dumps(value, default=str)
            if tags:
                client.setex(key, ttl, payload)
                tag_key = f"tag:{hashlib.md5(','.join(sorted(tags)).encode()).hexdigest()}"
                client.sadd(tag_key, key)
                client.expire(tag_key, ttl)
            else:
                client.setex(key, ttl, payload)
            with self._lock:
                self._stats.size += 1
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Cache set failed: %s", exc)
            return False

    def delete(self, key: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        try:
            result = client.delete(key)
            if result:
                with self._lock:
                    self._stats.size = max(0, self._stats.size - 1)
            return bool(result)
        except Exception as exc:  # noqa: BLE001
            logger.error("Cache delete failed: %s", exc)
            return False

    def invalidate_tag(self, tag: str) -> int:
        client = self._get_client()
        if not client:
            return 0
        try:
            tag_key = f"tag:{hashlib.md5(tag.encode()).hexdigest()}"
            keys = client.smembers(tag_key)
            if keys:
                client.delete(*keys)
                client.delete(tag_key)
                with self._lock:
                    self._stats.size = max(0, self._stats.size - len(keys))
                return len(keys)
            return 0
        except Exception as exc:  # noqa: BLE001
            logger.error("Cache tag invalidation failed: %s", exc)
            return 0

    def invalidate_prefix(self, prefix: str) -> int:
        client = self._get_client()
        if not client:
            return 0
        try:
            keys = client.keys(f"{prefix}*")
            if keys:
                client.delete(*keys)
                with self._lock:
                    self._stats.size = max(0, self._stats.size - len(keys))
                return len(keys)
            return 0
        except Exception as exc:  # noqa: BLE001
            logger.error("Cache prefix invalidation failed: %s", exc)
            return 0

    def clear(self) -> None:
        client = self._get_client()
        if client:
            try:
                client.flushdb()
            except Exception as exc:  # noqa: BLE001
                logger.error("Cache clear failed: %s", exc)
        with self._lock:
            self._stats = CacheStats()

    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: int = 300) -> Any:
        value = self.get(key)
        if value is not None:
            return value
        value = factory()
        self.set(key, value, ttl)
        return value

    def stats(self) -> Dict[str, Any]:
        client = self._get_client()
        if client:
            try:
                info = client.info("memory")
                self._stats.memory_bytes = info.get("used_memory", 0)
            except Exception:  # noqa: BLE001
                pass
        return {
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "hit_rate": round(self._stats.hit_rate, 4),
            "size": self._stats.size,
            "memory_bytes": self._stats.memory_bytes,
        }

    def close(self) -> None:
        for client in self._pool:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
        self._pool.clear()


distributed_cache = DistributedCache()
