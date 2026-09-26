"""Rate limiting with sliding window."""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict, deque
import time


@dataclass
class RateLimit:
    key: str
    limit: int
    window_seconds: int
    remaining: int = 0
    reset_at: datetime = None

    def __post_init__(self):
        if self.reset_at is None:
            self.reset_at = datetime.now(timezone.utc)


class RateLimiter:
    _windows: Dict[str, deque] = defaultdict(deque)
    _limits: Dict[str, tuple[int, int]] = {}

    @classmethod
    def configure(cls, key: str, limit: int, window_seconds: int) -> None:
        cls._limits[key] = (limit, window_seconds)

    @classmethod
    def check(cls, key: str) -> RateLimit:
        limit, window = cls._limits.get(key, (100, 60))
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
        rate_limit = RateLimit(
            key=key,
            limit=limit,
            window_seconds=window,
            remaining=max(0, remaining),
            reset_at=reset_at,
        )
        if not rate_limit.remaining:
            logger.warning("Rate limit exceeded for %s: %d/%d", key, limit, limit)
        return rate_limit

    @classmethod
    def reset(cls, key: str) -> None:
        cls._windows.pop(key, None)
