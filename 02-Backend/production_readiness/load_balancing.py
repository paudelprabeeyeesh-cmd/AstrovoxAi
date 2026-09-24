"""Load balancing algorithms and health checks."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class LoadBalancingStrategy:
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"


@dataclass
class BackendNode:
    id: str
    host: str
    port: int
    weight: int = 1
    active_connections: int = 0
    healthy: bool = True
    last_health_check: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "host": self.host,
            "port": self.port,
            "weight": self.weight,
            "active_connections": self.active_connections,
            "healthy": self.healthy,
        }


class LoadBalancer:
    def __init__(self, strategy: str = LoadBalancingStrategy.ROUND_ROBIN) -> None:
        self._strategy = strategy
        self._nodes: Dict[str, BackendNode] = {}
        self._lock = threading.Lock()
        self._round_robin_index: int = 0

    def register(self, node: BackendNode) -> None:
        with self._lock:
            self._nodes[node.id] = node

    def unregister(self, node_id: str) -> None:
        with self._lock:
            self._nodes.pop(node_id, None)

    def health_check(self, node_id: str, healthy: bool) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is not None:
                node.healthy = healthy
                node.last_health_check = time.time()

    def select(self, strategy: Optional[str] = None) -> Optional[BackendNode]:
        selected = self._select(strategy or self._strategy)
        if selected is not None:
            selected.active_connections += 1
        return selected

    def release(self, node_id: str) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is not None and node.active_connections > 0:
                node.active_connections -= 1

    def _select(self, strategy: str) -> Optional[BackendNode]:
        with self._lock:
            healthy = [node for node in self._nodes.values() if node.healthy]
            if not healthy:
                return None
            if strategy == LoadBalancingStrategy.ROUND_ROBIN:
                node = healthy[self._round_robin_index % len(healthy)]
                self._round_robin_index += 1
                return node
            if strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                return min(healthy, key=lambda n: n.active_connections)
            if strategy == LoadBalancingStrategy.RANDOM:
                import random
                return healthy[random.randint(0, len(healthy) - 1)]
            if strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                total = sum(n.weight for n in healthy)
                if total == 0:
                    return healthy[0]
                idx = self._round_robin_index % total
                self._round_robin_index += 1
                for node in healthy:
                    if idx < node.weight:
                        return node
                    idx -= node.weight
            return healthy[0]

    def nodes(self) -> List[BackendNode]:
        with self._lock:
            return list(self._nodes.values())

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {"healthy": sum(1 for n in self._nodes.values() if n.healthy), "total": len(self._nodes), "strategy": self._strategy}

    def run_health_checks(self, checker: Callable[[BackendNode], bool]) -> Dict[str, Any]:
        results = {}
        for node_id in list(self._nodes.keys()):
            node = self._nodes[node_id]
            try:
                healthy = checker(node)
                self.health_check(node_id, healthy)
                results[node_id] = healthy
            except Exception as _e:  # noqa: BLE001
                logger.error("health check failed for %s: %s", node_id, _e)
                self.health_check(node_id, False)
                results[node_id] = False
        return results
