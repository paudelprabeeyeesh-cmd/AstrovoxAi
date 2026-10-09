import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple


class APIResponseCache:
    def __init__(self, max_entries: int = 1024):
        self.max_entries = max_entries
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def _make_key(self, method: str, path: str, params: Dict[str, Any]) -> str:
        raw = f"{method}:{path}:{sorted(params.items())}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def set(self, method: str, path: str, params: Dict[str, Any], value: Any, ttl: float = 60.0, tags: Optional[List[str]] = None):
        key = self._make_key(method, path, params)
        self._evict_if_needed()
        self._cache[key] = (value, time.time(), tags or [])
        return type("CacheEntry", (), {"key": key})()

    def get(self, method: str, path: str, params: Dict[str, Any]) -> Optional[Any]:
        key = self._make_key(method, path, params)
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, _, _ = entry
        return value

    def invalidate_tag(self, tag: str) -> int:
        removed = 0
        for key in list(self._cache.keys()):
            _, _, tags = self._cache[key]
            if tag in tags:
                del self._cache[key]
                removed += 1
        return removed

    def invalidate_prefix(self, prefix: str) -> int:
        removed = 0
        for key in list(self._cache.keys()):
            if key.startswith(prefix):
                del self._cache[key]
                removed += 1
        return removed

    def _evict_if_needed(self) -> None:
        while len(self._cache) >= self.max_entries:
            if not self._cache:
                break
            oldest = min(self._cache.items(), key=lambda kv: kv[1][1])
            del self._cache[oldest[0]]

    def stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
        }
