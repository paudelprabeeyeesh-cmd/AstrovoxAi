import threading
import time
import secrets
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class Strategy(Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    IP_HASH = "ip_hash"


@dataclass
class BackendNode:
    node_id: str
    host: str
    port: int
    weight: int = 1
    active_connections: int = 0
    is_healthy: bool = True
    response_time_ms: float = 0.0
    last_checked: float = field(default_factory=time.time)


@dataclass
class RoutingDecision:
    node_id: str
    host: str
    port: int
    strategy: str
    ip_hash_used: bool = False


class LoadBalancer:
    def __init__(
        self,
        strategy: Strategy = Strategy.ROUND_ROBIN,
        health_check_interval: float = 10.0,
        ip_hash_key: str = "",
    ):
        self._strategy = strategy
        self._nodes: Dict[str, BackendNode] = {}
        self._lock = threading.Lock()
        self._round_robin_counter: Dict[str, int] = {}
        self._weighted_accumulator: Dict[str, float] = {}
        self._ip_hash_key = ip_hash_key or secrets.token_hex(16)
        self._health_check_interval = health_check_interval
        self._next_node_id = 0

    def add_node(
        self,
        node_id: str,
        host: str,
        port: int,
        weight: int = 1,
    ) -> BackendNode:
        with self._lock:
            node = BackendNode(
                node_id=node_id,
                host=host,
                port=port,
                weight=weight,
            )
            self._nodes[node_id] = node
            return node

    def remove_node(self, node_id: str):
        with self._lock:
            self._nodes.pop(node_id, None)

    def update_health(self, node_id: str, is_healthy: bool):
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.is_healthy = is_healthy
                node.last_checked = time.time()

    def _healthy_nodes(self) -> List[BackendNode]:
        return [n for n in self._nodes.values() if n.is_healthy]

    def _select_round_robin(self, nodes: List[BackendNode]) -> BackendNode:
        if not nodes:
            raise ValueError("No healthy nodes available")
        for node in nodes:
            self._round_robin_counter[node.node_id] = self._round_robin_counter.get(node.node_id, -1) + 1
        key = max(self._round_robin_counter, key=lambda k: self._round_robin_counter[k])
        return next(n for n in nodes if n.node_id == key)

    def _select_least_connections(self, nodes: List[BackendNode]) -> BackendNode:
        if not nodes:
            raise ValueError("No healthy nodes available")
        return min(nodes, key=lambda n: (n.active_connections, n.node_id))

    def _select_weighted(self, nodes: List[BackendNode]) -> BackendNode:
        if not nodes:
            raise ValueError("No healthy nodes available")
        total_weight = sum(n.weight for n in nodes)
        if total_weight == 0:
            return self._select_round_robin(nodes)
        for node in nodes:
            self._weighted_accumulator[node.node_id] = (
                self._weighted_accumulator.get(node.node_id, 0.0) + node.weight
            )
        accs = [(self._weighted_accumulator[n.node_id], n.node_id) for n in nodes]
        accs.sort(key=lambda x: x[0])
        return next(n for n in nodes if n.node_id == accs[0][1])

    def _select_random(self, nodes: List[BackendNode]) -> BackendNode:
        if not nodes:
            raise ValueError("No healthy nodes available")
        return secrets.SystemRandom().choice(nodes)

    def _select_ip_hash(self, nodes: List[BackendNode], client_ip: str) -> BackendNode:
        if not nodes:
            raise ValueError("No healthy nodes available")
        h = 0
        for ch in f"{self._ip_hash_key}:{client_ip}":
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        return nodes[h % len(nodes)]

    def route(self, client_ip: Optional[str] = None) -> RoutingDecision:
        with self._lock:
            nodes = self._healthy_nodes()
            if not nodes:
                raise ValueError("No healthy nodes available")
            if self._strategy == Strategy.ROUND_ROBIN:
                node = self._select_round_robin(nodes)
            elif self._strategy == Strategy.LEAST_CONNECTIONS:
                node = self._select_least_connections(nodes)
            elif self._strategy == Strategy.WEIGHTED_ROUND_ROBIN:
                node = self._select_weighted(nodes)
            elif self._strategy == Strategy.RANDOM:
                node = self._select_random(nodes)
            elif self._strategy == Strategy.IP_HASH:
                node = self._select_ip_hash(nodes, client_ip or "")
            else:
                node = self._select_round_robin(nodes)
            node.active_connections += 1
            return RoutingDecision(
                node_id=node.node_id,
                host=node.host,
                port=node.port,
                strategy=self._strategy.value,
                ip_hash_used=self._strategy == Strategy.IP_HASH,
            )

    def release(self, node_id: str):
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.active_connections = max(0, node.active_connections - 1)

    def record_response_time(self, node_id: str, response_time_ms: float):
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.response_time_ms = response_time_ms
                node.last_checked = time.time()

    @property
    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    @property
    def healthy_count(self) -> int:
        return len(self._healthy_nodes())

    @property
    def strategy(self) -> str:
        return self._strategy.value

    @property
    def all_nodes(self) -> Dict[str, Dict]:
        with self._lock:
            return {
                nid: {
                    "node_id": n.node_id,
                    "host": n.host,
                    "port": n.port,
                    "weight": n.weight,
                    "is_healthy": n.is_healthy,
                    "active_connections": n.active_connections,
                }
                for nid, n in self._nodes.items()
            }

    def mark_unhealthy(self, node_id: str):
        self.update_health(node_id, False)

    def mark_healthy(self, node_id: str):
        self.update_health(node_id, True)
