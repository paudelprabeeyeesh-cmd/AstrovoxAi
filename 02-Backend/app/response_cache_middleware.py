"""Response cache middleware for HTTP responses."""

import hashlib
import json
import logging
import time
from typing import Callable, Optional, Any, Dict, List

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.performance import Cache

logger = logging.getLogger("astravox.response_cache")


class CacheInvalidationHook:
    """Registry for cache invalidation hooks."""

    def __init__(self) -> None:
        self._hooks: Dict[str, List[Callable[[str], None]]] = {}

    def register(self, path_prefix: str, hook: Callable[[str], None]) -> None:
        """Register an invalidation hook for a path prefix."""
        if path_prefix not in self._hooks:
            self._hooks[path_prefix] = []
        self._hooks[path_prefix].append(hook)

    def trigger(self, path: str) -> None:
        """Trigger all hooks matching a path."""
        for prefix, hooks in self._hooks.items():
            if path.startswith(prefix) or prefix in path:
                for hook in hooks:
                    try:
                        hook(path)
                    except Exception as exc:
                        logger.debug("Cache invalidation hook error: %s", exc)

    def clear(self) -> None:
        """Clear all registered hooks."""
        self._hooks.clear()


cache_invalidation_hooks = CacheInvalidationHook()


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """Cache GET responses to reduce redundant processing."""

    def __init__(
        self,
        app,
        ttl_seconds: int = 300,
        max_size: int = 1000,
        cacheable_methods: Optional[set] = None,
        cacheable_content_types: Optional[set] = None,
    ) -> None:
        super().__init__(app)
        self._cache = Cache(ttl_seconds=ttl_seconds, max_size=max_size)
        self._cacheable_methods = cacheable_methods or {"GET"}
        self._cacheable_content_types = cacheable_content_types or {
            "application/json",
            "text/plain",
        }

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        if request.method not in self._cacheable_methods:
            return await call_next(request)

        cache_key = self._make_key(request)
        cached_response = self._cache.get(cache_key)
        if cached_response is not None:
            logger.debug("Cache hit for %s %s", request.method, request.url.path)
            return Response(
                content=cached_response["body"],
                status_code=cached_response["status_code"],
                headers=cached_response["headers"],
                media_type=cached_response.get("media_type", "application/json"),
            )

        response = await call_next(request)

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            if any(ct in content_type for ct in self._cacheable_content_types):
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                self._cache.set(cache_key, {
                    "body": body,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type,
                })
                cache_invalidation_hooks.trigger(str(request.url.path))
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=response.headers,
                    media_type=response.media_type,
                )

        return response

    def _make_key(self, request: Request) -> str:
        key_data = json.dumps({
            "method": request.method,
            "path": str(request.url.path),
            "query": str(request.url.query),
        }, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    def invalidate(self, path: str) -> None:
        """Invalidate cache entries matching a path prefix."""
        keys_to_delete = [
            key for key in list(self._cache._cache.keys())
            if path in key
        ]
        for key in keys_to_delete:
            self._cache.invalidate(key)
        cache_invalidation_hooks.trigger(path)

    def clear(self) -> None:
        self._cache.clear()

    @property
    def stats(self) -> dict:
        return {
            "hit_rate": self._cache.hit_rate,
            "size": len(self._cache._cache),
        }
