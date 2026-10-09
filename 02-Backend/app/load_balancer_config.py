"""Load balancer configuration for AstrovoxAI backend.

Supports round-robin, weighted, least-connections, and health-aware strategies.
"""

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BackendNode:
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100
    healthy: bool = True
    active_connections: int = 0
    last_health_check: float = 0.0
    response_time_ms: float = 0.0

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def load_ratio(self) -> float:
        if self.max_connections <= 0:
            return 1.0
        return self.active_connections / self.max_connections


class LoadBalancerConfig:
    """Load balancer with multiple strategies and health checking."""

    def __init__(
        self,
        strategy: str = "round_robin",
        health_check_interval: float = 30.0,
        unhealthy_threshold: int = 3,
    ):
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.unhealthy_threshold = unhealthy_threshold
        self._nodes: Dict[str, BackendNode] = {}
        self._lock = threading.Lock()
        self._current_index = 0
        self._health_thread: Optional[threading.Thread] = None
        self._running = False

    def register_node(self, node: BackendNode) -> None:
        with self._lock:
            self._nodes[node.address] = node
        logger.info("Registered backend node: %s", node.address)

    def deregister_node(self, address: str) -> None:
        with self._lock:
            self._nodes.pop(address, None)
        logger.info("Deregistered backend node: %s", address)

    def select_node(self) -> Optional[BackendNode]:
        with self._lock:
            healthy = [n for n in self._nodes.values() if n.healthy]
            if not healthy:
                return None
            if self.strategy == "round_robin":
                node = healthy[self._current_index % len(healthy)]
                self._current_index += 1
                return node
            if self.strategy == "weighted":
                return max(healthy, key=lambda n: n.weight / max(n.load_ratio, 0.01))
            if self.strategy == "least_connections":
                return min(healthy, key=lambda n: n.active_connections)
            if self.strategy == "response_time":
                return min(healthy, key=lambda n: n.response_time_ms)
        return healthy[0]

    def increment_connections(self, address: str) -> None:
        with self._lock:
            node = self._nodes.get(address)
            if node:
                node.active_connections += 1

    def decrement_connections(self, address: str) -> None:
        with self._lock:
            node = self._nodes.get(address)
            if node and node.active_connections > 0:
                node.active_connections -= 1

    def mark_unhealthy(self, address: str) -> None:
        with self._lock:
            node = self._nodes.get(address)
            if node:
                node.healthy = False
                logger.warning("Marked backend node unhealthy: %s", address)

    def mark_healthy(self, address: str) -> None:
        with self._lock:
            node = self._nodes.get(address)
            if node:
                node.healthy = True
                logger.info("Marked backend node healthy: %s", address)

    def start_health_checks(self, check_func) -> None:
        self._running = True

        def _run():
            while self._running:
                time.sleep(self.health_check_interval)
                try:
                    for node in list(self._nodes.values()):
                        healthy = check_func(node)
                        if healthy:
                            self.mark_healthy(node.address)
                        else:
                            self.mark_unhealthy(node.address)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Health check error: %s", exc)

        self._health_thread = threading.Thread(target=_run, daemon=True)
        self._health_thread.start()

    def stop_health_checks(self) -> None:
        self._running = False
        if self._health_thread:
            self._health_thread.join(timeout=5)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "strategy": self.strategy,
                "total_nodes": len(self._nodes),
                "healthy_nodes": sum(1 for n in self._nodes.values() if n.healthy),
                "nodes": [
                    {
                        "address": n.address,
                        "healthy": n.healthy,
                        "active_connections": n.active_connections,
                        "load_ratio": round(n.load_ratio, 3),
                        "response_time_ms": n.response_time_ms,
                    }
                    for n in self._nodes.values()
                ],
            }


load_balancer = LoadBalancerConfig()
