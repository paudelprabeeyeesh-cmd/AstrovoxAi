import logging
import threading
import time
from collections import defaultdict, deque
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiterService:
    def __init__(self):
        self._windows: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_allowed(self, key: str, limit: int = 60, window: int = 60) -> bool:
        now = time.time()
        window_start = now - window
        with self._lock:
            self._windows[key] = deque([t for t in self._windows[key] if t > window_start])
            if len(self._windows[key]) >= limit:
                logger.warning("Rate limit exceeded for %s", key)
                return False
            self._windows[key].append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._windows[key].clear()


rate_limiter_service = RateLimiterService()
