"""Tool rate limiting."""

from typing import Dict
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import defaultdict, deque
import time


@dataclass
class ToolRateLimit:
    tool_name: str
    user_id: str
    limit: int
    window_seconds: int
    remaining: int = 0
    reset_at: datetime = None

    def __post_init__(self):
        if self.reset_at is None:
            self.reset_at = datetime.now(timezone.utc)


class ToolRateLimiter:
    _limits: Dict[str, tuple[int, int]] = {}
    _windows: Dict[str, deque] = defaultdict(deque)

    @classmethod
    def configure(cls, tool_name: str, limit: int, window_seconds: int) -> None:
        cls._limits[tool_name] = (limit, window_seconds)

    @classmethod
    def check(cls, tool_name: str, user_id: str) -> ToolRateLimit:
        limit, window = cls._limits.get(tool_name, (100, 60))
        key = f"{tool_name}:{user_id}"
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
        return ToolRateLimit(
            tool_name=tool_name,
            user_id=user_id,
            limit=limit,
            window_seconds=window,
            remaining=max(0, remaining),
            reset_at=reset_at,
        )
