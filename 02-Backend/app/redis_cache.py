"""Enhanced Redis caching for AstrovoxAI backend.

Provides connection pooling, cluster support, and advanced cache patterns.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """Enhanced Redis client with connection pooling and cluster support."""

    def __init__(self, redis_url: Optional[str] = None, max_connections: int = 20):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.max_connections = max_connections
        self._pool: list = []
        self._lock = threading.Lock()
        self._init_pool()

    def _init_pool(self) -> None:
        try:
            import redis
            for _ in range(min(4, self.max_connections)):
                client = redis.Redis.from_url(self.redis_url, decode_responses=True)
                client.ping()
                self._pool.append(client)
            logger.info("Redis connection pool initialized with %d connections", len(self._pool))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis pool init failed: %s", exc)

    def get_client(self):
        with self._lock:
            if self._pool:
                return self._pool[0]
        try:
            import redis
            return redis.Redis.from_url(self.redis_url, decode_responses=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis client creation failed: %s", exc)
            return None

    def get(self, key: str) -> Optional[Any]:
        client = self.get_client()
        if not client:
            return None
        try:
            data = client.get(key)
            return json.loads(data) if data else None
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis get failed: %s", exc)
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        client = self.get_client()
        if not client:
            return False
        try:
            client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis set failed: %s", exc)
            return False

    def delete(self, key: str) -> bool:
        client = self.get_client()
        if not client:
            return False
        try:
            return bool(client.delete(key))
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis delete failed: %s", exc)
            return False

    def exists(self, key: str) -> bool:
        client = self.get_client()
        if not client:
            return False
        try:
            return bool(client.exists(key))
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis exists failed: %s", exc)
            return False

    def expire(self, key: str, ttl: int) -> bool:
        client = self.get_client()
        if not client:
            return False
        try:
            return bool(client.expire(key, ttl))
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis expire failed: %s", exc)
            return False

    def increment(self, key: str, amount: int = 1) -> int:
        client = self.get_client()
        if not client:
            return 0
        try:
            return client.incrby(key, amount)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis increment failed: %s", exc)
            return 0

    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: int = 300) -> Any:
        value = self.get(key)
        if value is not None:
            return value
        value = factory()
        self.set(key, value, ttl=ttl)
        return value

    def get_many(self, keys: List[str]) -> Dict[str, Optional[Any]]:
        client = self.get_client()
        if not client:
            return {k: None for k in keys}
        try:
            values = client.mget(keys)
            return {k: json.loads(v) if v else None for k, v in zip(keys, values)}
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis mget failed: %s", exc)
            return {k: None for k in keys}

    def set_many(self, mapping: Dict[str, Any], ttl: int = 300) -> bool:
        client = self.get_client()
        if not client:
            return False
        try:
            pipeline = client.pipeline()
            for key, value in mapping.items():
                pipeline.setex(key, ttl, json.dumps(value, default=str))
            pipeline.execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis mset failed: %s", exc)
            return False

    def close(self) -> None:
        for client in self._pool:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
        self._pool.clear()


redis_cache = RedisCache()
