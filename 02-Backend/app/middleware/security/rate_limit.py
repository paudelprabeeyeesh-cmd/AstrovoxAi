import os
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse


class InMemoryRateLimiter:
    """Per-IP sliding-window limiter with automatic cleanup."""

    def __init__(self, limit: str = "120/minute"):
        self.limit = limit
        self.requests: Dict[Tuple[str, int], int] = defaultdict(int)
        self.lock = Lock()
        self.window_seconds = self._parse_window(limit)
        self.max_requests = self._parse_max(limit)
        self._last_cleanup = time.time()
    def is_allowed(self, client_ip: str) -> Tuple[bool, int, int]:
        now = int(time.time())
        window_start = now - self.window_seconds
        key = (client_ip, window_start)

        # Periodic cleanup every 60 seconds
        if now - self._last_cleanup > 60:
            with self.lock:
                self._cleanup()

    )
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"x-ratelimit-limit": str(limit), "x-ratelimit-remaining": "0"},
        )
    return response

