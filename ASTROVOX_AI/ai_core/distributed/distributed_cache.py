from typing import Any, Optional, Dict
import time
import threading
from collections import OrderedDict


class DistributedCache:
    def __init__(self, max_size: int = 10000, default_ttl: float = 3600.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.store: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.store:
                self.stats['misses'] += 1
                return None
            value, expiry = self.store[key]
            if time.time() > expiry:
                del self.store[key]
                self.stats['misses'] += 1
                return None
            self.stats['hits'] += 1
            self.store.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        with self.lock:
            if key in self.store:
                self.store.move_to_end(key)
            self.store[key] = (value, time.time() + (ttl or self.default_ttl))
            if len(self.store) > self.max_size:
                self.store.popitem(last=False)
                self.stats['evictions'] += 1

    def delete(self, key: str) -> None:
        with self.lock:
            self.store.pop(key, None)

    def clear(self) -> None:
        with self.lock:
            self.store.clear()
            self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()
