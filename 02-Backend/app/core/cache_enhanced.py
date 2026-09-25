"""Enhanced caching with Redis, LRU fallback, and response caching."""

import hashlib
import json
import logging
import time
from functools import lru_cache, wraps
from typing import Any, Callable, Coroutine, Optional, TypeVar

logger = logging.getLogger(__name__)

try:
    import redis
    _redis_available = True
except ImportError:
    _redis_available = False

_redis_client = None

F = TypeVar("F", bound=Callable[..., Any])


def get_redis_client():
    global _redis_client
    if not _redis_available:
        return None
    if _redis_client is None:
        try:
            import os
            url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            _redis_client = redis.Redis.from_url(url, decode_responses=True, socket_timeout=5)
            _redis_client.ping()
        except Exception as exc:
            logger.warning(f"Redis unavailable: {exc}")
            _redis_client = None
    return _redis_client


def cache_key(*args: Any, **kwargs: Any) -> str:
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = "cache"):
    """Decorator: cache function results in Redis with TTL, fallback to in-memory LRU."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            client = get_redis_client()
            ck = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            if client:
                cached_value = client.get(ck)
                if cached_value is not None:
                    return json.loads(cached_value)
            result = func(*args, **kwargs)
            if client:
                try:
                    client.setex(ck, ttl, json.dumps(result, default=str))
                except Exception as exc:
                    logger.debug(f"Cache set failed: {exc}")
            return result

        return wrapper  # type: ignore

    return decorator


def async_cached(ttl: int = 300, key_prefix: str = "cache"):
    """Decorator: cache async function results in Redis with TTL."""

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            client = get_redis_client()
            ck = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            if client:
                cached_value = client.get(ck)
                if cached_value is not None:
                    return json.loads(cached_value)
            result = await func(*args, **kwargs)
            if client:
                try:
                    client.setex(ck, ttl, json.dumps(result, default=str))
                except Exception as exc:
                    logger.debug(f"Async cache set failed: {exc}")
            return result

        return wrapper

    return decorator


class LRUCache:
    """Simple bounded LRU cache for in-memory fallback."""

    def __init__(self, maxsize: int = 128):
        self._cache: dict[str, Any] = {}
        self._order: list[str] = []
        self._maxsize = maxsize

    def get(self, key: str) -> Any:
        if key in self._cache:
            self._order.remove(key)
            self._order.append(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self._maxsize:
            oldest = self._order.pop(0)
            del self._cache[oldest]
        self._cache[key] = value
        self._order.append(key)

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)
        if key in self._order:
            self._order.remove(key)

    def clear(self) -> None:
        self._cache.clear()
        self._order.clear()


_response_cache = LRUCache(maxsize=256)


def cache_response(key: str, value: Any, ttl: Optional[int] = None) -> None:
    client = get_redis_client()
    if client and ttl:
        try:
            client.setex(key, ttl, json.dumps(value, default=str))
            return
        except Exception:
            pass
    _response_cache.set(key, value)


def get_cached_response(key: str) -> Any:
    client = get_redis_client()
    if client:
        value = client.get(key)
        if value is not None:
            return json.loads(value)
    return _response_cache.get(key)


def invalidate_cache(key: str) -> None:
    client = get_redis_client()
    if client:
        try:
            client.delete(key)
        except Exception:
            pass
    _response_cache.invalidate(key)
