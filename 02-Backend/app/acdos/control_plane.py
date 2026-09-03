"""ACDOS Control Plane: cluster coordinator, service registry, leader election,
node discovery, resource scheduler, health management.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from . import make_id, now, now_iso
from ..logging_config import get_logger

logger = get_logger(__name__)


class NodeState(str, Enum):
    JOINING = "joining"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DRAINING = "draining"
    DEAD = "dead"


class ZoneState(str, Enum):
    ACTIVE = "active"
    READ_ONLY = "read_only"
    OFFLINE = "offline"


@dataclass
class Node:
    id: str
    address: str
    zone: str = "default"
    region: str = "default"
    role: str = "worker"
    state: NodeState = NodeState.JOINING
    capacity: Dict[str, float] = field(default_factory=dict)
    used: Dict[str, float] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=now)
    started_at: float = field(default_factory=now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "address": self.address,
            "zone": self.zone,
            "region": self.region,
            "role": self.role,
            "state": self.state.value,
            "capacity": dict(self.capacity),
            "used": dict(self.used),
            "last_heartbeat": self.last_heartbeat,
            "uptime_s": round(now() - self.started_at, 2),
            "metadata": dict(self.metadata),
        }


@dataclass
class Zone:
    name: str
    region: str
    state: ZoneState = ZoneState.ACTIVE
    nodes: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "region": self.region,
            "state": self.state.value,
            "nodes": sorted(self.nodes),
        }


class LeaderElector:
    """Cluster leader election with TTL and epoch."""

    def __init__(self, ttl: float = 15.0) -> None:
        self._leader: Optional[str] = None
        self._expires_at: float = 0.0
        self._ttl = ttl
        self._epoch = 0
        self._lock = threading.Lock()

    def try_become_leader(self, candidate_id: str) -> bool:
        with self._lock:
            if self._leader and self._expires_at > now() and candidate_id != self._leader:
                return False
            self._leader = candidate_id
            self._epoch += 1
            self._expires_at = now() + self._ttl
            return True

    def leader(self) -> Optional[str]:
        with self._lock:
            if self._leader and self._expires_at > now():
                return self._leader
            return None

    def renew(self) -> bool:
        with self._lock:
            if self._leader is None:
                return False
            self._expires_at = now() + self._ttl
            return True

    def step_down(self) -> None:
        with self._lock:
            self._leader = None
            self._expires_at = 0.0

    def status(self) -> Dict[str, Any]:
        return {
            "leader": self.leader(),
            "epoch": self._epoch,
            "expires_at": self._expires_at,
        }


class ClusterCoordinator:
    """Central control plane: nodes, zones, leader election, scheduler, upgrades."""

    HEARTBEAT_TIMEOUT = 30.0

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._zones: Dict[str, Zone] = {}
        self._services: Dict[str, Set[str]] = defaultdict(set)  # service -> node ids
        self._leader = LeaderElector()
        self._config: Dict[str, Any] = {}
        self._config_version: Dict[str, int] = defaultdict(int)
        self._listeners: List[Callable[[str, Any], None]] = []
        self._upgrades: List[Dict[str, Any]] = []

    # ---- node discovery ------------------------------------------------

    def add_node(self, node: Node) -> Node:
        node.id = node.id or make_id("node")
        node.state = NodeState.HEALTHY
        node.last_heartbeat = now()
        self._nodes[node.id] = node
        self._zones.setdefault(
            node.zone, Zone(name=node.zone, region=node.region)
        ).nodes.add(node.id)
        self._emit("node.joined", node.to_dict())
        return node

    def remove_node(self, node_id: str) -> Optional[Node]:
        node = self._nodes.pop(node_id, None)
        if node is None:
            return None
        zone = self._zones.get(node.zone)
        if zone is not None:
            zone.nodes.discard(node_id)
        self._emit("node.left", node.to_dict())
        return node

    def heartbeat(self, node_id: str) -> bool:
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.last_heartbeat = now()
        if node.state == NodeState.JOINING:
            node.state = NodeState.HEALTHY
        return True

    def list_nodes(self, only_healthy: bool = False) -> List[Node]:
        nodes = list(self._nodes.values())
        if only_healthy:
            nodes = [
                n
                for n in nodes
                if n.state == NodeState.HEALTHY
                and now() - n.last_heartbeat < self.HEARTBEAT_TIMEOUT
            ]
        return nodes

    def detect_dead(self) -> List[str]:
        dead: List[str] = []
        for node in list(self._nodes.values()):
            if now() - node.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                node.state = NodeState.DEAD
                dead.append(node.id)
                self._emit("node.dead", node.to_dict())
        return dead

    # ---- zones ----------------------------------------------------------

    def zone(self, name: str, region: str = "default") -> Zone:
        if name not in self._zones:
            self._zones[name] = Zone(name=name, region=region)
        return self._zones[name]

    def set_zone_state(self, name: str, state: ZoneState) -> None:
        self._zones[name].state = state
        self._emit("zone.state", {"zone": name, "state": state.value})

    # ---- service registry ----------------------------------------------

    def register_service(self, service: str, node_id: str) -> None:
        self._services[service].add(node_id)

    def deregister_service(self, service: str, node_id: str) -> None:
        self._services[service].discard(node_id)

    def discover(self, service: str) -> List[str]:
        return sorted(self._services.get(service, set()))

    # ---- leader election ----------------------------------------------

    def try_become_leader(self, candidate_id: str) -> bool:
        ok = self._leader.try_become_leader(candidate_id)
        if ok:
            self._emit("leader.elected", {"leader": candidate_id, "epoch": self._leader._epoch})
        return ok

    def leader(self) -> Optional[str]:
        return self._leader.leader()

    def renew_leadership(self) -> bool:
        return self._leader.renew()

    def step_down(self) -> None:
        self._leader.step_down()
        self._emit("leader.step_down", {})

    # ---- configuration -------------------------------------------------

    def set_config(self, key: str, value: Any) -> int:
        self._config[key] = value
        self._config_version[key] += 1
        self._emit("config.updated", {"key": key, "version": self._config_version[key]})
        return self._config_version[key]

    def get_config(self, key: str) -> Any:
        return self._config.get(key)

    def config_version(self, key: str) -> int:
        return self._config_version.get(key, 0)

    # ---- resource scheduler -------------------------------------------

    def schedule(
        self,
        requirements: Dict[str, float],
        *,
        zone: Optional[str] = None,
    ) -> Optional[Node]:
        candidates = self.list_nodes(only_healthy=True)
        if zone:
            candidates = [n for n in candidates if n.zone == zone]
        if not candidates:
            return None
        candidates.sort(
            key=lambda n: sum(
                n.used.get(k, 0) / max(n.capacity.get(k, 1), 1)
                for k in requirements
            )
        )
        return candidates[0]

    def allocate(self, node_id: str, requirements: Dict[str, float]) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        for resource, amount in requirements.items():
            cap = node.capacity.get(resource, 0)
            used = node.used.get(resource, 0)
            if used + amount > cap:
                return False
        for resource, amount in requirements.items():
            node.used[resource] = node.used.get(resource, 0) + amount
        return True

    def release(self, node_id: str, requirements: Dict[str, float]) -> None:
        node = self._nodes.get(node_id)
        if node is None:
            return
        for resource, amount in requirements.items():
            node.used[resource] = max(0, node.used.get(resource, 0) - amount)

    # ---- cluster upgrades ---------------------------------------------

    def start_upgrade(self, target_version: str) -> Dict[str, Any]:
        upgrade_id = make_id("upgrade")
        record = {
            "id": upgrade_id,
            "target_version": target_version,
            "started_at": now(),
            "status": "in_progress",
            "nodes_updated": 0,
        }
        self._upgrades.append(record)
        self._emit("upgrade.started", record)
        return record

    def complete_upgrade(self, upgrade_id: str) -> bool:
        for record in self._upgrades:
            if record["id"] == upgrade_id:
                record["status"] = "completed"
                record["completed_at"] = now()
                self._emit("upgrade.completed", record)
                return True
        return False

    def upgrades(self) -> List[Dict[str, Any]]:
        return list(self._upgrades)

    # ---- events --------------------------------------------------------

    def subscribe(self, listener: Callable[[str, Any], None]) -> None:
        self._listeners.append(listener)

    def _emit(self, event: str, payload: Any) -> None:
        for listener in self._listeners:
            try:
                listener(event, payload)
            except Exception:
                continue

    # ---- status --------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = defaultdict(int)
        for n in self._nodes.values():
            by_state[n.state.value] += 1
        return {
            "nodes": len(self._nodes),
            "by_state": dict(by_state),
            "zones": [z.to_dict() for z in self._zones.values()],
            "services": {s: sorted(nodes) for s, nodes in self._services.items()},
            "leader": self.leader(),
            "config_keys": list(self._config.keys()),
        }


_GLOBAL_COORDINATOR: Optional[ClusterCoordinator] = None


def get_cluster_coordinator() -> ClusterCoordinator:
    global _GLOBAL_COORDINATOR
    if _GLOBAL_COORDINATOR is None:
        _GLOBAL_COORDINATOR = ClusterCoordinator()
    return _GLOBAL_COORDINATOR