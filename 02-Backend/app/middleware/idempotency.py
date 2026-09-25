"""Idempotency key enforcement middleware.

Stores processed idempotency keys (method + path + key) in-memory
with a TTL to prevent duplicate POST/PUT/PATCH/DELETE requests
from causing duplicate side effects.
"""

from __future__ import annotations

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


_store = _IdempotencyStore()


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Reject duplicate state-changing requests that carry the same
    Idempotency-Key header within the TTL window."""

    def __init__(self, app, ttl_seconds: float = 86400.0) -> None:
        super().__init__(app)
        self._store = _IdempotencyStore(ttl_seconds=ttl_seconds)

    async def dispatch(self, request: Request, call_next):
        if request.method not in _IDEMPOTENT_METHODS:
            return await call_next(request)

        key_header = request.headers.get("Idempotency-Key")
        if not key_header:
            return await call_next(request)

        composite = f"{request.method}:{request.url.path}:{key_header}"
        if self._store.seen(composite):
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Duplicate request detected",
                    "code": "IDEMPOTENT_REQUEST_DUPLICATE",
                },
            )

        self._store.mark(composite)
        response = await call_next(request)
        return response
