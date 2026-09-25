"""Idempotency key enforcement middleware.

Stores processed idempotency keys (method + path + key) in Redis
with a TTL to prevent duplicate POST/PUT/PATCH/DELETE requests
from causing duplicate side effects. Falls back to in-memory store
when Redis is unavailable.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Optional, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("astravox.idempotency")

_IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_IDEMPOTENCY_PREFIX = "idempotency:"


class _IdempotencyStore:
    def __init__(self, ttl_seconds: float = 86400.0, max_entries: int = 100_000) -> None:
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
        self._max = max_entries
        self._entries: "OrderedDict[str, float]" = OrderedDict()

    def _prune(self) -> None:
        cutoff = time.time() - self._ttl
        keys = [k for k, ts in self._entries.items() if ts < cutoff]
        for k in keys:
            del self._entries[k]

    def seen(self, key: str) -> bool:
        with self._lock:
            self._prune()
            if len(self._entries) > self._max:
                self._entries.popitem(last=False)
            return key in self._entries

    def mark(self, key: str) -> None:
        with self._lock:
            self._entries[key] = time.time()
            self._entries.move_to_end(key)

    def stats(self) -> dict:
        with self._lock:
            self._prune()
            return {"entries": len(self._entries), "max": self._max, "ttl_seconds": self._ttl}


class _RedisIdempotencyStore:
    def __init__(self, ttl_seconds: float = 86400.0) -> None:
        self._ttl = int(ttl_seconds)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                from app.core.config import get_config
                config = get_config()
                self._client = aioredis.from_url(
                    config.redis.url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            except Exception as exc:
                logger.warning("Redis idempotency store unavailable: %s", exc)
                return None
        return self._client

    async def seen(self, key: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            result = await client.exists(key)
            return bool(result)
        except Exception as exc:
            logger.warning("Redis idempotency check failed: %s", exc)
            return False

    async def mark(self, key: str) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            await client.setex(key, self._ttl, "1")
        except Exception as exc:
            logger.warning("Redis idempotency mark failed: %s", exc)

    async def stats(self) -> dict:
        client = self._get_client()
        if client is None:
            return {"backend": "unavailable"}
        try:
            info = await client.info("memory")
            return {
                "backend": "redis",
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        except Exception:
            return {"backend": "redis", "status": "error"}


_store = _IdempotencyStore()
_redis_store: Optional[_RedisIdempotencyStore] = None


def _get_redis_store() -> Optional[_RedisIdempotencyStore]:
    global _redis_store
    if _redis_store is None:
        try:
            from app.core.config import get_config
            get_config()
            _redis_store = _RedisIdempotencyStore()
        except Exception:
            return None
    return _redis_store


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Reject duplicate state-changing requests that carry the same
    Idempotency-Key header within the TTL window."""

    def __init__(self, app, ttl_seconds: float = 86400.0, use_redis: bool = True) -> None:
        super().__init__(app)
        self._ttl = ttl_seconds
        self._use_redis = use_redis
        self._redis = _get_redis_store() if use_redis else None
        self._fallback = _IdempotencyStore(ttl_seconds=ttl_seconds)

    async def dispatch(self, request: Request, call_next):
        if request.method not in _IDEMPOTENT_METHODS:
            return await call_next(request)

        key_header = request.headers.get("Idempotency-Key")
        if not key_header:
            return await call_next(request)

        composite = f"{_IDEMPOTENCY_PREFIX}{request.method}:{request.url.path}:{key_header}"
        digest = hashlib.sha256(composite.encode()).hexdigest()
        cache_key = f"{_IDEMPOTENCY_PREFIX}{digest}"

        if self._redis is not None:
            seen = await self._redis.seen(cache_key)
            if seen:
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": "Duplicate request detected",
                        "code": "IDEMPOTENT_REQUEST_DUPLICATE",
                    },
                )
            await self._redis.mark(cache_key)
        else:
            if self._fallback.seen(cache_key):
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": "Duplicate request detected",
                        "code": "IDEMPOTENT_REQUEST_DUPLICATE",
                    },
                )
            self._fallback.mark(cache_key)

        response = await call_next(request)
        return response