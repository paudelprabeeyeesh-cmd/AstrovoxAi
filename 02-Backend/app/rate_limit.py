import os
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse


class InMemoryRateLimiter:
    """Simple per-IP sliding-window limiter for local deployments."""

    def __init__(self, limit: str = "120/minute"):
        self.limit = limit
        self.requests: Dict[Tuple[str, int], int] = defaultdict(int)
        self.lock = Lock()
        self.window_seconds = self._parse_window(limit)
        self.max_requests = self._parse_max(limit)

    def _parse_max(self, limit: str) -> int:
        value = limit.split("/")[0]
        return int(value) if value.isdigit() else 120

    def _parse_window(self, limit: str) -> int:
        window = limit.split("/", 1)[1] if "/" in limit else "minute"
        return {"second": 1, "minute": 60, "hour": 3600}.get(window.lower(), 60)

    def is_allowed(self, client_ip: str) -> Tuple[bool, int, int]:
        now = int(time.time())
        window_start = now - self.window_seconds
        key = (client_ip, window_start)
        with self.lock:
            self.requests[key] += 1
            remaining = max(0, self.max_requests - self.requests[key])
            return self.requests[key] <= self.max_requests, remaining, self.max_requests


rate_limiter = InMemoryRateLimiter(os.getenv("RATE_LIMIT", "120/minute"))


async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    allowed, remaining, limit = rate_limiter.is_allowed(client_ip)
    response = await call_next(request)
    response.headers["x-ratelimit-limit"] = str(limit)
    response.headers["x-ratelimit-remaining"] = str(remaining)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:8000 https://*.supabase.co"
    )
    if not allowed:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}, headers={"x-ratelimit-limit": str(limit), "x-ratelimit-remaining": "0"})
    return response
