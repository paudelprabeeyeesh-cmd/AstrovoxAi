import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CacheEntry:
    key: str
    value: Any
    version: int
    ttl: float
    created_at: float = field(default_factory=time.time)
    node_id: str = "local"


class ConsistencyProtocol:
    def __init__(self, consistency: str = "eventual") -> None:
        self.consistency = consistency
        self._store: Dict[str, CacheEntry] = {}
        self._version_vector: Dict[str, int] = {}
        self._lock_time = 0.0

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() - entry.created_at > entry.ttl:
            self._store.pop(key, None)
            return None
        return entry.value

    def put(self, key: str, value: Any, ttl: float = 60.0, node_id: str = "local") -> None:
        version = self._version_vector.get(node_id, 0) + 1
        self._version_vector[node_id] = version
        entry = CacheEntry(key=key, value=value, version=version, ttl=ttl, node_id=node_id)
        self._store[key] = entry
        if self.consistency == "strong":
            self._replicate(key, entry)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def _replicate(self, key: str, entry: CacheEntry) -> None:
        self._store[key] = entry

    def merge(self, incoming: List[CacheEntry]) -> None:
        for entry in incoming:
            existing = self._store.get(entry.key)
            if existing is None or entry.version > existing.version:
                self._store[entry.key] = entry
                self._version_vector[entry.node_id] = max(
                    self._version_vector.get(entry.node_id, 0), entry.version
                )

    def stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._store),
            "consistency": self.consistency,
            "version_vector": dict(self._version_vector),
        }
