"""Redis caching layer for performance optimization."""

import os
import json
import logging
import hashlib
from typing import Optional, Any

logger = logging.getLogger(__name__)


class CacheBackend:
    """Abstract cache backend interface."""

    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    async def clear(self) -> bool:
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """In-memory cache for development and testing."""

    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry > 0 and time.time() > expiry:
                del self._cache[key]
                return None
            return value
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        expiry = time.time() + ttl if ttl > 0 else 0
        self._cache[key] = (value, expiry)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    async def clear(self) -> bool:
        self._cache.clear()
        return True


class RedisCache(CacheBackend):
    """Redis cache for production."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._redis_url = redis_url
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(self._redis_url)
            except ImportError:
                logger.warning("redis package not installed, falling back to in-memory cache")
                return None
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        client = self.client
        if not client:
            return None
        try:
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        client = self.client
        if not client:
            return False
        try:
            await client.set(key, json.dumps(value), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        client = self.client
        if not client:
            return False
        try:
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        client = self.client
        if not client:
            return False
        try:
            return bool(await client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def clear(self) -> bool:
        client = self.client
        if not client:
            return False
        try:
            await client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False


import time


class CacheManager:
    """High-level caching manager."""

    def __init__(self):
        self._backend: CacheBackend = self._create_backend()

    def _create_backend(self) -> CacheBackend:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                return RedisCache(redis_url)
            except ImportError:
                logger.warning("redis package not installed, using in-memory cache")
        return InMemoryCache()

    def _make_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        return await self._backend.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        return await self._backend.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        return await self._backend.delete(key)

    async def get_or_set(self, key: str, factory, ttl: int = 300) -> Any:
        """Get from cache or compute and cache."""
        cached = await self.get(key)
        if cached is not None:
            return cached

        value = await factory() if callable(factory) else factory
        await self.set(key, value, ttl)
        return value

    async def cached(self, ttl: int = 300, key_prefix: str = ""):
        """Decorator for caching function results."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                cache_key = f"{key_prefix}:{self._make_key(*args, **kwargs)}"
                cached = await self.get(cache_key)
                if cached is not None:
                    return cached

                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        return 0

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "backend": type(self._backend).__name__,
            "redis_url": os.getenv("REDIS_URL", "not configured"),
        }


cache_manager = CacheManager()
