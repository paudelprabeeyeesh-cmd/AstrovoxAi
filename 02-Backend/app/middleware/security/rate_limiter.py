import os
import time
import logging
from collections import defaultdict
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self):
        self.windows = defaultdict(list)
        self.enabled = os.getenv("RATE_LIMIT_ENABLED", "1") == "1"
        self.default_max = int(os.getenv("RATE_LIMIT_DEFAULT", "60"))
        self.window_seconds = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    def check(self, key: str, max_requests: int = None) -> bool:
        if not self.enabled:
            return True
        limit = max_requests or self.default_max
        now = time.time()
        window_start = now - self.window_seconds
        self.windows[key] = [t for t in self.windows[key] if t > window_start]
        if len(self.windows[key]) >= limit:
            logger.warning(f"Rate limit exceeded for {key}: {len(self.windows[key])}/{limit}")
            return False
        self.windows[key].append(now)
        return True


rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    user_id = getattr(request.state, "user_id", None)
    key = user_id or client_ip
    if not rate_limiter.check(key):
        raise HTTPException(status_code=429, detail="Too many requests")
    return await call_next(request)
