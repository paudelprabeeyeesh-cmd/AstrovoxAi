import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class Node:
    node_id: str
    endpoint: str
    state: NodeState = NodeState.HEALTHY
    last_heartbeat: float = field(default_factory=time.time)


class FailoverController:
    def __init__(self, active_node_id: str) -> None:
        self._active_node_id = active_node_id
        self._previous_node_id: Optional[str] = None
        self._nodes: Dict[str, Node] = {}
        self._lock = threading.Lock()

    def register_node(self, node_id: str, endpoint: str) -> None:
        self._nodes[node_id] = Node(node_id=node_id, endpoint=endpoint)

    def health_check(self, node_id: str) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        return node.state == NodeState.HEALTHY

    def trigger_failover(self, target_node_id: str) -> Dict[str, Any]:
        with self._lock:
            if target_node_id not in self._nodes:
                raise ValueError("Unknown node")
            node = self._nodes[target_node_id]
            if node.state == NodeState.FAILED:
                raise RuntimeError("Target node is failed")
            self._previous_node_id = self._active_node_id
            self._active_node_id = target_node_id
            node.state = NodeState.HEALTHY
            return {
                "previous_active": self._previous_node_id,
                "new_active": target_node_id,
                "timestamp": time.time(),
            }

    def rollback(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._previous_node_id is None:
                return None
            target = self._previous_node_id
            self._previous_node_id = self._active_node_id
            self._active_node_id = target
            if target in self._nodes:
                self._nodes[target].state = NodeState.HEALTHY
            return {
                "previous_active": self._previous_node_id,
                "new_active": target,
                "timestamp": time.time(),
            }

    def get_active_node(self) -> Optional[str]:
        return self._active_node_id

    def mark_failed(self, node_id: str) -> None:
        node = self._nodes.get(node_id)
        if node is not None:
            node.state = NodeState.FAILED
            node.last_heartbeat = time.time()
