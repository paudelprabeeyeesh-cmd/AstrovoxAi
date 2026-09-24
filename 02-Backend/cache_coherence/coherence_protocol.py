import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from cache_coherence.invalidation_service import InvalidationService
from cache_coherence.replication_tracker import ReplicationTracker
from cache_coherence.version_vector import VersionVector


@dataclass
class CacheEntry:
    key: str
    value: Any
    version_vector: VersionVector
    timestamp: float = field(default_factory=time.time)
    invalidated: bool = False


class CoherenceProtocol:
    def __init__(
        self,
        node_id: str,
        invalidation_service: Optional[InvalidationService] = None,
        replication_tracker: Optional[ReplicationTracker] = None,
    ) -> None:
        self.node_id = node_id
        self._entries: Dict[str, CacheEntry] = {}
        self._invalidation_service = invalidation_service or InvalidationService()
        self._replication_tracker = replication_tracker or ReplicationTracker(node_id)

    def put(self, key: str, value: Any) -> CacheEntry:
        vv = VersionVector()
        vv.increment(self.node_id)
        entry = CacheEntry(key=key, value=value, version_vector=vv)
        self._entries[key] = entry
        if self._invalidation_service:
            self._invalidation_service.record_write(key, self.node_id)
        if self._replication_tracker:
            self._replication_tracker.record_write(key, self.node_id)
        return entry

    def get(self, key: str) -> Any:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.invalidated:
            return None
        return entry.value

    def invalidate_key(self, key: str, source_node: str) -> None:
        entry = self._entries.get(key)
        if entry:
            entry.invalidated = True
        self._invalidation_service.invalidate(key, source_node)
        self._replication_tracker.on_invalidation(key, source_node)

    def invalidate_all(self, source_node: str) -> List[str]:
        keys = []
        for key, entry in self._entries.items():
            entry.invalidated = True
            keys.append(key)
        self._invalidation_service.invalidate_all(source_node)
        return keys

    def merge_from(self, other_entries: Dict[str, CacheEntry]) -> None:
        for key, remote_entry in other_entries.items():
            local_entry = self._entries.get(key)
            if local_entry is None:
                if not remote_entry.invalidated:
                    self._entries[key] = remote_entry
                continue
            if local_entry.invalidated and not remote_entry.invalidated:
                self._entries[key] = remote_entry
                continue
            if not local_entry.invalidated and remote_entry.invalidated:
                continue
            if local_entry.version_vector.compare(remote_entry.version_vector):
                continue
            if remote_entry.version_vector.compare(local_entry.version_vector):
                if not remote_entry.invalidated:
                    self._entries[key] = remote_entry
                continue
            self._entries[key] = remote_entry

    def on_remote_put(self, remote_entry: CacheEntry) -> None:
        key = remote_entry.key
        local_entry = self._entries.get(key)
        if local_entry is None:
            self._entries[key] = remote_entry
            return
        local_vv = local_entry.version_vector
        remote_vv = remote_entry.version_vector
        if remote_vv.compare(local_vv):
            self._entries[key] = remote_entry
        elif not local_vv.compare(remote_vv):
            self._entries[key] = remote_entry

    def check_coherence(self, key: str) -> bool:
        entry = self._entries.get(key)
        if entry is None:
            return True
        return not entry.invalidated

    def snapshot(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "entries": {
                key: {
                    "key": e.key,
                    "value": e.value,
                    "version_vector": e.version_vector.to_dict(),
                    "timestamp": e.timestamp,
                    "invalidated": e.invalidated,
                }
                for key, e in self._entries.items()
            },
        }

    def stats(self) -> Dict[str, Any]:
        total = len(self._entries)
        invalidated = sum(1 for e in self._entries.values() if e.invalidated)
        return {
            "node_id": self.node_id,
            "total_entries": total,
            "valid_entries": total - invalidated,
            "invalidated_entries": invalidated,
        }
