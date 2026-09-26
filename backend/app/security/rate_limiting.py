"""Rate limiting with sliding window and per-identifier tracking."""
import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    key: str
    limit: int
    window_seconds: int
    remaining: int = 0
    reset_at: Optional[datetime] = None


class RateLimiter:
    _windows: Dict[str, deque] = defaultdict(deque)
    _limits: Dict[str, tuple[int, int]] = {"default": (100, 60)}

    @classmethod
    def configure(cls, key: str, limit: int, window_seconds: int) -> None:
        cls._limits[key] = (limit, window_seconds)

    @classmethod
    def check(cls, key: str) -> RateLimit:
        limit, window = cls._limits.get(key, cls._limits["default"])
        now = time.time()
        window_start = now - window
        timestamps = cls._windows[key]
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()
        remaining = max(0, limit - len(timestamps))
        if len(timestamps) < limit:
            timestamps.append(now)
            remaining -= 1
        reset_at = datetime.fromtimestamp(timestamps[0] + window, tz=timezone.utc) if timestamps else datetime.now(timezone.utc)
        return RateLimit(
            key=key,
            limit=limit,
            window_seconds=window,
            remaining=max(0, remaining),
            reset_at=reset_at,
        )

    @classmethod
    def reset(cls, key: str) -> None:
        cls._windows.pop(key, None)

    @classmethod
    def get_stats(cls) -> Dict[str, int]:
        return {"tracked_keys": len(cls._windows)}


rate_limiter = RateLimiter()
