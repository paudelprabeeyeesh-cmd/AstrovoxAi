import os
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse


class InMemoryRateLimiter:
<<<<<<< HEAD
    """Per-IP sliding-window limiter with automatic cleanup."""
=======
    """Simple per-IP sliding-window limiter for local deployments."""
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838

    def __init__(self, limit: str = "120/minute"):
        self.limit = limit
        self.requests: Dict[Tuple[str, int], int] = defaultdict(int)
        self.lock = Lock()
        self.window_seconds = self._parse_window(limit)
        self.max_requests = self._parse_max(limit)
<<<<<<< HEAD
        self._last_cleanup = time.time()
=======
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838

    def _parse_max(self, limit: str) -> int:
        value = limit.split("/")[0]
        return int(value) if value.isdigit() else 120

    def _parse_window(self, limit: str) -> int:
        window = limit.split("/", 1)[1] if "/" in limit else "minute"
        return {"second": 1, "minute": 60, "hour": 3600}.get(window.lower(), 60)

<<<<<<< HEAD
    def _cleanup(self):
        """Remove expired entries to prevent memory leak."""
        now = int(time.time())
        cutoff = now - self.window_seconds * 2
        expired_keys = [k for k in self.requests if k[1] < cutoff]
        for key in expired_keys:
            del self.requests[key]
        self._last_cleanup = time.time()

=======
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838
    def is_allowed(self, client_ip: str) -> Tuple[bool, int, int]:
        now = int(time.time())
        window_start = now - self.window_seconds
        key = (client_ip, window_start)
<<<<<<< HEAD

        # Periodic cleanup every 60 seconds
        if now - self._last_cleanup > 60:
            with self.lock:
                self._cleanup()

=======
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838
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
<<<<<<< HEAD
        "default-src 'self'; img-src 'self' data: https:; style-src 'self'; "
        "script-src 'self'; connect-src 'self' http://localhost:8000 https://*.supabase.co"
=======
        "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:8000 https://*.supabase.co"
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838
    )
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"x-ratelimit-limit": str(limit), "x-ratelimit-remaining": "0"},
        )
    return response
