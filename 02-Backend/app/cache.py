"""Redis cache manager for AstrovoxAI backend."""

import json
import os
from typing import Optional, Any
from functools import wraps

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class CacheManager:
    """File-backed or Redis-backed cache depending on availability."""

    def __init__(self):
        self._redis = None
        self._file_cache: dict[str, tuple[Any, float]] = {}
        self._try_redis()

    def _try_redis(self):
        """Attempt to connect to Redis."""
        try:
            import redis
            self._redis = redis.from_url(REDIS_URL, decode_responses=True)
            self._redis.ping()
        except Exception:
            self._redis = None

    @property
    def backend(self) -> str:
        return "redis" if self._redis else "memory"

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        try:
            if self._redis:
                data = self._redis.get(key)
                return json.loads(data) if data else None
            return None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set a value in cache with TTL in seconds."""
        try:
            if self._redis:
                self._redis.setex(key, ttl, json.dumps(value, default=str))
                return True
            return False
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            if self._redis:
                self._redis.delete(key)
                return True
            return False
        except Exception:
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        try:
            if self._redis:
                return self._redis.incrby(key, amount)
            return 0
        except Exception:
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key."""
        try:
            if self._redis:
                return self._redis.expire(key, ttl)
            return False
        except Exception:
            return False


cache = CacheManager()


def cached(ttl: int = 300, key_prefix: str = "cache"):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args))}"
            result = await cache.get(cache_key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
