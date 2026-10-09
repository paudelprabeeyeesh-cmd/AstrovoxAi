import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class InvalidationRecord:
    key: str
    source_node: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


class InvalidationService:
    def __init__(self) -> None:
        self._invalidated_keys: Set[str] = set()
        self._history: Dict[str, List[InvalidationRecord]] = {}
        self._pending_acks: Dict[str, Set[str]] = {}

    def invalidate(self, key: str, source_node: str) -> None:
        self._invalidated_keys.add(key)
        record = InvalidationRecord(key=key, source_node=source_node)
        self._history.setdefault(key, []).append(record)
        pending_nodes = self._pending_acks.get(key, set())
        if pending_nodes:
            record.acknowledged = True

    def invalidate_all(self, source_node: str) -> None:
        self._invalidated_keys.clear()

    def is_invalidated(self, key: str) -> bool:
        return key in self._invalidated_keys

    def acknowledge(self, key: str, node_id: str) -> None:
        pending = self._pending_acks.get(key, set())
        pending.discard(node_id)
        self._pending_acks[key] = pending
        for record in self._history.get(key, []):
            record.acknowledged = True

    def invalidate_with_ack(self, key: str, source_node: str, ack_nodes: Set[str]) -> None:
        self.invalidate(key, source_node)
        self._pending_acks[key] = ack_nodes.copy()

    def record_write(self, key: str, node_id: str) -> None:
        self._invalidated_keys.discard(key)
        pending = self._pending_acks.get(key, set())
        pending.discard(node_id)
        self._pending_acks[key] = pending

    def history(self, key: str) -> List[Dict[str, Any]]:
        return [
            {
                "key": r.key,
                "source_node": r.source_node,
                "timestamp": r.timestamp,
                "acknowledged": r.acknowledged,
            }
            for r in self._history.get(key, [])
        ]

    def pending_acks(self) -> Dict[str, Set[str]]:
        return {k: v for k, v in self._pending_acks.items() if v}

    def cleanup(self, max_age: float = 300.0) -> int:
        now = time.time()
        cleaned = 0
        for key in list(self._invalidated_keys):
            records = self._history.get(key, [])
            if records and now - records[-1].timestamp > max_age:
                self._invalidated_keys.discard(key)
                self._history.pop(key, None)
                self._pending_acks.pop(key, None)
                cleaned += 1
        return cleaned

    def stats(self) -> Dict[str, Any]:
        total_pending = sum(len(v) for v in self._pending_acks.values())
        return {
            "invalidated_keys": len(self._invalidated_keys),
            "pending_acks": total_pending,
            "history_keys": len(self._history),
        }
