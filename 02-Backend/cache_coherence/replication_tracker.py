import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class ReplicaRecord:
    key: str
    node_id: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


@dataclass
class ReplicationEvent:
    key: str
    source_node: str
    target_nodes: Set[str]
    timestamp: float = field(default_factory=time.time)
    completed: bool = False


class ReplicationTracker:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._replicas: Dict[str, List[ReplicaRecord]] = {}
        self._events: Dict[str, ReplicationEvent] = {}
        self._key_nodes: Dict[str, Set[str]] = {}

    def record_write(self, key: str, node_id: str) -> None:
        self._key_nodes.setdefault(key, set()).add(node_id)
        record = ReplicaRecord(key=key, node_id=node_id)
        self._replicas.setdefault(key, []).append(record)

    def replicate_to(self, key: str, source_node: str, target_nodes: Set[str]) -> None:
        event = ReplicationEvent(key=key, source_node=source_node, target_nodes=target_nodes)
        self._events[key] = event
        self._key_nodes.setdefault(key, set()).update(target_nodes)
        for node_id in target_nodes:
            self._key_nodes.setdefault(key, set()).add(node_id)

    def on_invalidation(self, key: str, source_node: str) -> None:
        event = self._events.get(key)
        if event:
            event.completed = True
        for record in self._replicas.get(key, []):
            if record.node_id == source_node:
                record.acknowledged = True

    def acknowledge_replica(self, key: str, node_id: str) -> None:
        for record in self._replicas.get(key, []):
            if record.node_id == node_id:
                record.acknowledged = True
        event = self._events.get(key)
        if event:
            event.target_nodes.discard(node_id)
            if not event.target_nodes:
                event.completed = True

    def is_replicated(self, key: str, node_id: str) -> bool:
        return node_id in self._key_nodes.get(key, set())

    def nodes_for_key(self, key: str) -> Set[str]:
        return set(self._key_nodes.get(key, set()))

    def incomplete_events(self) -> List[ReplicationEvent]:
        return [e for e in self._events.values() if not e.completed]

    def stats(self) -> Dict[str, Any]:
        total_keys = len(self._key_nodes)
        incomplete = len(self.incomplete_events())
        return {
            "node_id": self.node_id,
            "tracked_keys": total_keys,
            "incomplete_replications": incomplete,
        }
