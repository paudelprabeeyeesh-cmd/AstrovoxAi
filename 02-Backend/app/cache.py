<<<<<<< HEAD
"""Redis caching layer for performance optimization."""

import os
import json
import logging
import hashlib
import time
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
=======
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
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838
