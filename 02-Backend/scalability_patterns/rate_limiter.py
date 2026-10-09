import threading
import time
from typing import Dict, List, Optional


class RateLimiter:
    def __init__(self, default_max: int = 60, window: int = 60) -> None:
        self.default_max = default_max
        self.window = window
        self._enabled = True
        self._tokens: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def check(self, key: str, max_requests: Optional[int] = None) -> bool:
        if not self._enabled:
            return True
        limit = max_requests or self.default_max
        now = time.monotonic()
        with self._lock:
            timestamps = self._tokens.get(key, [])
            timestamps = [t for t in timestamps if now - t <= self.window]
            if len(timestamps) >= limit:
                self._tokens[key] = timestamps
                return False
            timestamps.append(now)
            self._tokens[key] = timestamps
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._tokens.pop(key, None)

    def remaining(self, key: str) -> int:
        if not self._enabled:
            return self.default_max
        now = time.monotonic()
        with self._lock:
            timestamps = self._tokens.get(key, [])
            timestamps = [t for t in timestamps if now - t <= self.window]
            self._tokens[key] = timestamps
            return max(0, self.default_max - len(timestamps))
