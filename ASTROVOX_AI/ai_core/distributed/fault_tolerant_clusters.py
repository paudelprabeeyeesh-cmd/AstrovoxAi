"""Fault-tolerant cluster management for distributed inference."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ClusterNodeStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"


@dataclass
class ClusterNode:
    node_id: str
    host: str
    port: int
    gpu_ids: List[int] = None
    status: ClusterNodeStatus = ClusterNodeStatus.HEALTHY
    load: float = 0.0
    last_health_check: datetime = None
    total_requests: int = 0
    failed_requests: int = 0

    def __post_init__(self):
        if self.gpu_ids is None:
            self.gpu_ids = []
        if self.last_health_check is None:
            self.last_health_check = datetime.utcnow()


class FaultTolerantCluster:
    def __init__(self, nodes: Optional[List[ClusterNode]] = None, health_check_interval: float = 10.0, failure_threshold: int = 3):
        self.nodes: List[ClusterNode] = nodes or []
        self.health_check_interval = health_check_interval
        self.failure_threshold = failure_threshold
        self._node_index: Dict[str, ClusterNode] = {n.node_id: n for n in self.nodes}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_node(self, node: ClusterNode) -> None:
        self.nodes.append(node)
        self._node_index[node.node_id] = node
        logger.info("Registered cluster node %s", node.node_id)

    def unregister_node(self, node_id: str) -> None:
        if node_id in self._node_index:
            node = self._node_index.pop(node_id)
            self.nodes = [n for n in self.nodes if n.node_id != node_id]
            logger.info("Unregistered cluster node %s", node_id)

    def get_healthy_nodes(self) -> List[ClusterNode]:
        return [n for n in self.nodes if n.status == ClusterNodeStatus.HEALTHY]

    def get_best_node(self, strategy: str = "least_loaded") -> Optional[ClusterNode]:
        healthy = self.get_healthy_nodes()
        if not healthy:
            return None
        if strategy == "least_loaded":
            return min(healthy, key=lambda n: n.load)
        if strategy == "round_robin":
            return min(healthy, key=lambda n: n.total_requests)
        return healthy[0]

    def route_request(self, request: Any, strategy: str = "least_loaded") -> Tuple[Optional[ClusterNode], Optional[Any]]:
        node = self.get_best_node(strategy)
        if node is None:
            logger.error("No healthy nodes available")
            return None, None
        try:
            result = self._send_request(node, request)
            node.total_requests += 1
            node.load = max(0.0, node.load - 0.1)
            return node, result
        except Exception as exc:
            node.failed_requests += 1
            node.status = ClusterNodeStatus.DEGRADED if node.failed_requests < self.failure_threshold else ClusterNodeStatus.UNHEALTHY
            logger.exception("Request failed on node %s: %s", node.node_id, exc)
            return None, None

    def _send_request(self, node: ClusterNode, request: Any) -> Any:
        import requests
        url = f"http://{node.host}:{node.port}/infer"
        response = requests.post(url, json=request, timeout=30)
        response.raise_for_status()
        return response.json()

    def start_health_checks(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._health_loop, daemon=True)
        self._thread.start()

    def stop_health_checks(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _health_loop(self) -> None:
        while self._running:
            self.perform_health_checks()
            time.sleep(self.health_check_interval)

    def perform_health_checks(self) -> Dict[str, ClusterNodeStatus]:
        results = {}
        for node in self.nodes:
            try:
                import requests
                url = f"http://{node.host}:{node.port}/health"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    node.status = ClusterNodeStatus.HEALTHY
                else:
                    node.status = ClusterNodeStatus.DEGRADED
            except Exception:
                node.status = ClusterNodeStatus.UNHEALTHY
            results[node.node_id] = node.status
            node.last_health_check = datetime.utcnow()
        return results

    def get_cluster_status(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "healthy_nodes": len(self.get_healthy_nodes()),
            "total_requests": sum(n.total_requests for n in self.nodes),
            "failed_requests": sum(n.failed_requests for n in self.nodes),
            "avg_load": sum(n.load for n in self.nodes) / max(len(self.nodes), 1),
        }


import threading
