"""Caching infrastructure with Redis Sentinel and Cluster support."""

from __future__ import annotations

import json
import logging
import pickle
from typing import Any, Dict, Optional

import redis

from app.core.config import get_config

logger = logging.getLogger(__name__)


class Cache:
    """Redis-based cache with Sentinel and Cluster support."""

    def __init__(self) -> None:
        self._config = get_config()
        self._redis: Optional[redis.Redis] = None
        self._memory_cache: Dict[str, Any] = {}
        self._connect()

    def _connect(self) -> None:
        try:
            if hasattr(self._config, 'redis_sentinel_url') and self._config.redis_sentinel_url:
                from redis.sentinel import Sentinel
                sentinel = Sentinel(
                    self._config.redis.sentinel_url.split(','),
                    socket_timeout=self._config.redis.socket_timeout,
                    socket_connect_timeout=self._config.redis.socket_connect_timeout,
                )
                self._redis = sentinel.master_for(
                    service_name='redis-master',
                    redis_class=redis.Redis,
                    max_connections=self._config.redis.max_connections,
                )
            elif self._config.redis.url:
                self._redis = redis.Redis.from_url(
                    self._config.redis.url,
                    max_connections=self._config.redis.max_connections,
                    socket_timeout=self._config.redis.socket_timeout,
                    socket_connect_timeout=self._config.redis.socket_connect_timeout,
                )
            self._redis.ping()
            logger.info("Connected to Redis")
        except Exception as exc:
            logger.warning(f"Redis connection failed, using in-memory cache: {exc}")
            self._redis = None

    def get(self, key: str) -> Optional[Any]:
        if self._redis:
            try:
                value = self._redis.get(key)
                if value is not None:
                    return pickle.loads(value)
            except Exception as exc:
                logger.warning(f"Redis get failed: {exc}")
        return self._memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if self._redis:
            try:
                serialized = pickle.dumps(value)
                if ttl:
                    self._redis.setex(key, ttl, serialized)
                else:
                    self._redis.set(key, serialized)
            except Exception as exc:
                logger.warning(f"Redis set failed: {exc}")
                self._memory_cache[key] = value
        else:
            self._memory_cache[key] = value

    def delete(self, key: str) -> None:
        if self._redis:
            try:
                self._redis.delete(key)
            except Exception as exc:
                logger.warning(f"Redis delete failed: {exc}")
        self._memory_cache.pop(key, None)

    def clear(self) -> None:
        if self._redis:
            try:
                self._redis.flushdb()
            except Exception as exc:
                logger.warning(f"Redis flush failed: {exc}")
        self._memory_cache.clear()


_cache = Cache()


def get_cache() -> Cache:
    return _cache
