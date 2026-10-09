from typing import Any, Dict, List, Optional


class PrefixCache:
    def __init__(self, max_entries: int = 1024):
        self.max_entries = max_entries
        self._store: Dict[str, Dict[str, Any]] = {}
        self._prefix_keys: Dict[str, List[str]] = {}

    def _make_key(self, prefix: str, identifier: str) -> str:
        return f"{prefix}:{identifier}"

    def set(self, prefix: str, identifier: str, value: Any) -> None:
        key = self._make_key(prefix, identifier)
        self._evict_if_needed()
        self._store[key] = value
        self._prefix_keys.setdefault(prefix, []).append(key)

    def get(self, prefix: str, identifier: str) -> Optional[Any]:
        key = self._make_key(prefix, identifier)
        return self._store.get(key)

    def get_by_prefix(self, prefix: str) -> List[Any]:
        keys = self._prefix_keys.get(prefix, [])
        return [self._store[k] for k in keys if k in self._store]

    def invalidate_prefix(self, prefix: str) -> int:
        keys = self._prefix_keys.pop(prefix, [])
        removed = 0
        for key in keys:
            if self._store.pop(key, None) is not None:
                removed += 1
        return removed

    def delete(self, prefix: str, identifier: str) -> bool:
        key = self._make_key(prefix, identifier)
        if key in self._store:
            del self._store[key]
            if prefix in self._prefix_keys:
                try:
                    self._prefix_keys[prefix].remove(key)
                except ValueError:
                    pass
            return True
        return False

    def _evict_if_needed(self) -> None:
        while len(self._store) >= self.max_entries:
            if not self._store:
                break
            oldest = next(iter(self._store))
            del self._store[oldest]

    def stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._store),
            "prefixes": len(self._prefix_keys),
            "max_entries": self.max_entries,
        }
