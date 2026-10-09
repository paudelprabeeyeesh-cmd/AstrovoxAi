import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class WindowEntry:
    timestamp: float


class SlidingWindowRateLimiter:
    def __init__(self, window_seconds: float = 60.0, max_requests: int = 100):
        self._window_seconds = window_seconds
        self._max_requests = max_requests
        self._windows: Dict[str, List[WindowEntry]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, timestamp: Optional[float] = None) -> bool:
        if timestamp is None:
            timestamp = time.time()
        with self._lock:
            window = self._windows.setdefault(key, [])
            cutoff = timestamp - self._window_seconds
            self._compact(window, cutoff)
            if len(window) < self._max_requests:
                window.append(WindowEntry(timestamp=timestamp))
                return True
            return False

    def _compact(self, window: List[WindowEntry], cutoff: float):
        write_idx = 0
        for entry in window:
            if entry.timestamp >= cutoff:
                window[write_idx] = entry
                write_idx += 1
        del window[write_idx:]

    def count(self, key: str, timestamp: Optional[float] = None) -> int:
        if timestamp is None:
            timestamp = time.time()
        with self._lock:
            window = self._windows.get(key, [])
            cutoff = timestamp - self._window_seconds
            self._compact(window, cutoff)
            return len(window)

    def remaining(self, key: str, timestamp: Optional[float] = None) -> int:
        return max(0, self._max_requests - self.count(key, timestamp))

    def reset(self, key: str):
        with self._lock:
            self._windows.pop(key, None)

    @property
    def window_seconds(self) -> float:
        return self._window_seconds

    @property
    def max_requests(self) -> int:
        return self._max_requests
