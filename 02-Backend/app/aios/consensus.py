"""Consensus, distributed locks, configuration, membership, fault tolerance."""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from . import make_id, now


class DistributedLock:
    """Single-key lock with TTL and auto-release."""

    def __init__(self) -> None:
        self._holders: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def acquire(self, key: str, holder: str, ttl: float = 5.0) -> bool:
        with self._lock:
            current = self._holders.get(key)
            if current and current["expires_at"] > now() and current["holder"] != holder:
                return False
            self._holders[key] = {
                "holder": holder,
                "expires_at": now() + ttl,
            }
            return True

    def release(self, key: str, holder: str) -> bool:
        with self._lock:
            current = self._holders.get(key)
            if not current or current["holder"] != holder:
                return False
            del self._holders[key]
            return True

    def renew(self, key: str, holder: str, ttl: float = 5.0) -> bool:
        with self._lock:
            current = self._holders.get(key)
            if not current or current["holder"] != holder:
                return False
            current["expires_at"] = now() + ttl
            return True

    def holder(self, key: str) -> Optional[str]:
        current = self._holders.get(key)
        if not current or current["expires_at"] < now():
            return None
        return current["holder"]

    def sweep(self) -> int:
        with self._lock:
            expired = [k for k, v in self._holders.items() if v["expires_at"] < now()]
            for k in expired:
                del self._holders[k]
            return len(expired)


@dataclass
class Node:
    id: str
    address: str
    zone: str = "default"
    region: str = "default"
    role: str = "worker"
    healthy: bool = True
    last_seen: float = field(default_factory=now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "address": self.address,
            "zone": self.zone,
            "region": self.region,
            "role": self.role,
            "healthy": self.healthy,
            "last_seen": self.last_seen,
        }


class ClusterMembership:
    """Tracks cluster members and supports quorum checks."""

    def __init__(self, gossip_interval_s: float = 5.0) -> None:
        self._nodes: Dict[str, Node] = {}
        self._gossip_interval = gossip_interval_s
        self._listeners: List[Callable[[Node, str], None]] = []

    def add(self, node: Node) -> None:
        node.last_seen = now()
        self._nodes[node.id] = node
        self._emit(node, "joined")

    def remove(self, node_id: str) -> None:
        node = self._nodes.pop(node_id, None)
        if node is not None:
            self._emit(node, "left")

    def heartbeat(self, node_id: str) -> None:
        node = self._nodes.get(node_id)
        if node is not None:
            node.last_seen = now()
            node.healthy = True

    def mark_unhealthy(self, node_id: str) -> None:
        node = self._nodes.get(node_id)
        if node is not None:
            node.healthy = False
            self._emit(node, "unhealthy")

    def nodes(self, only_healthy: bool = False) -> List[Node]:
        out = list(self._nodes.values())
        if only_healthy:
            out = [n for n in out if n.healthy and now() - n.last_seen < self._gossip_interval * 3]
        return out

    def sweep(self) -> List[str]:
        stale = [
            n.id
            for n in self._nodes.values()
            if now() - n.last_seen > self._gossip_interval * 3
        ]
        for sid in stale:
            self.mark_unhealthy(sid)
        return stale

    def quorum(self, total: int, failures: int = 1) -> bool:
        return total - failures >= (total // 2) + 1

    def on_change(self, listener: Callable[[Node, str], None]) -> None:
        self._listeners.append(listener)

    def _emit(self, node: Node, event: str) -> None:
        for listener in self._listeners:
            try:
                listener(node, event)
            except Exception:
                continue

    def status(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes(only_healthy=True)],
            "total": len(self._nodes),
            "healthy": sum(1 for n in self._nodes.values() if n.healthy),
        }


class ConfigurationStore:
    """Replicated key-value configuration with versioned writes."""

    def __init__(self) -> None:
        self._values: Dict[str, Any] = {}
        self._versions: Dict[str, int] = defaultdict(int)
        self._replicas: Dict[str, List[Any]] = {}
        self._history: List[Dict[str, Any]] = []

    def set(self, key: str, value: Any, *, replicas: int = 2) -> int:
        self._versions[key] += 1
        self._values[key] = value
        self._replicas[key] = [value] * replicas
        self._history.append({"op": "set", "key": key, "version": self._versions[key], "ts": now()})
        if len(self._history) > 1000:
            self._history = self._history[-1000:]
        return self._versions[key]

    def get(self, key: str) -> Optional[Any]:
        return self._values.get(key)

    def version(self, key: str) -> int:
        return self._versions.get(key, 0)

    def watch(self, key: str) -> bool:
        return key in self._values

    def snapshot(self) -> Dict[str, Any]:
        return {
            "values": dict(self._values),
            "versions": dict(self._versions),
            "history_size": len(self._history),
        }


class ConsensusLayer:
    """Convenience facade for the consensus primitives."""

    def __init__(self) -> None:
        self.locks = DistributedLock()
        self.membership = ClusterMembership()
        self.config = ConfigurationStore()

    def status(self) -> Dict[str, Any]:
        return {
            "membership": self.membership.status(),
            "config": self.config.snapshot(),
            "active_locks": len(self.locks._holders),
        }


_GLOBAL_CONSENSUS: Optional[ConsensusLayer] = None


def get_consensus() -> ConsensusLayer:
    global _GLOBAL_CONSENSUS
    if _GLOBAL_CONSENSUS is None:
        _GLOBAL_CONSENSUS = ConsensusLayer()
    return _GLOBAL_CONSENSUS