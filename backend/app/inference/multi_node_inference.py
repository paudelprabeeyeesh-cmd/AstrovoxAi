"""Multi-node inference orchestration for distributed AI serving."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"


@dataclass
class InferenceNode:
    node_id: str
    host: str
    port: int
    gpu_ids: List[int] = field(default_factory=list)
    status: NodeStatus = NodeStatus.HEALTHY
    load: float = 0.0
    last_health_check: datetime = field(default_factory=datetime.utcnow)
    total_requests: int = 0
    failed_requests: int = 0


class MultiNodeInference:
    def __init__(self, nodes: Optional[List[InferenceNode]] = None, health_check_interval: float = 10.0):
        self.nodes: List[InferenceNode] = nodes or []
        self.health_check_interval = health_check_interval
        self._node_index: Dict[str, InferenceNode] = {n.node_id: n for n in self.nodes}
        self._last_health_check: datetime = datetime.utcnow()

    def register_node(self, node: InferenceNode) -> None:
        self.nodes.append(node)
        self._node_index[node.node_id] = node
        logger.info("Registered inference node %s at %s:%d", node.node_id, node.host, node.port)

    def unregister_node(self, node_id: str) -> None:
        if node_id in self._node_index:
            node = self._node_index.pop(node_id)
            self.nodes = [n for n in self.nodes if n.node_id != node_id]
            logger.info("Unregistered inference node %s", node_id)

    def get_healthy_nodes(self) -> List[InferenceNode]:
        return [n for n in self.nodes if n.status == NodeStatus.HEALTHY]

    def get_best_node(self, strategy: str = "least_loaded") -> Optional[InferenceNode]:
        healthy = self.get_healthy_nodes()
        if not healthy:
            return None
        if strategy == "least_loaded":
            return min(healthy, key=lambda n: n.load)
        if strategy == "round_robin":
            return min(healthy, key=lambda n: n.total_requests)
        return healthy[0]

    def route_request(self, request: Any, strategy: str = "least_loaded") -> Tuple[Optional[InferenceNode], Optional[Any]]:
        node = self.get_best_node(strategy)
        if node is None:
            logger.error("No healthy inference nodes available")
            return None, None
        try:
            result = self._send_request(node, request)
            node.total_requests += 1
            node.load = max(0.0, node.load - 0.1)
            return node, result
        except Exception as exc:
            node.failed_requests += 1
            node.status = NodeStatus.DEGRADED if node.failed_requests < 3 else NodeStatus.UNHEALTHY
            logger.exception("Request failed on node %s: %s", node.node_id, exc)
            return None, None

    def _send_request(self, node: InferenceNode, request: Any) -> Any:
        import requests
        url = f"http://{node.host}:{node.port}/infer"
        response = requests.post(url, json=request, timeout=30)
        response.raise_for_status()
        return response.json()

    def perform_health_checks(self) -> Dict[str, NodeStatus]:
        results = {}
        for node in self.nodes:
            try:
                import requests
                url = f"http://{node.host}:{node.port}/health"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    node.status = NodeStatus.HEALTHY
                else:
                    node.status = NodeStatus.DEGRADED
            except Exception:
                node.status = NodeStatus.UNHEALTHY
            results[node.node_id] = node.status
            node.last_health_check = datetime.utcnow()
        self._last_health_check = datetime.utcnow()
        return results

    def get_cluster_status(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "healthy_nodes": len(self.get_healthy_nodes()),
            "total_requests": sum(n.total_requests for n in self.nodes),
            "failed_requests": sum(n.failed_requests for n in self.nodes),
            "avg_load": sum(n.load for n in self.nodes) / max(len(self.nodes), 1),
        }
