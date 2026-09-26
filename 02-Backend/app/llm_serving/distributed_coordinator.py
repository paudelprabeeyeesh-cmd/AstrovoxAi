"""Distributed inference coordinator for multi-node LLM serving."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class NodeInfo:
    node_id: str
    host: str
    port: int
    gpus: list[dict[str, Any]]
    status: str = "healthy"
    last_heartbeat: float = field(default_factory=time.time)
    current_load: float = 0.0
    capacity: int = 1
    model_name: str = ""


@dataclass
class InferenceTask:
    task_id: str
    node_id: str
    request_id: str
    input_ids: Any
    max_new_tokens: int = 256
    priority: int = 2
    created_at: float = field(default_factory=time.time)
    assigned_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None


class DistributedCoordinator:
    def __init__(self, node_id: str, host: str, port: int, gpus: list[dict[str, Any]]):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.gpus = gpus
        self._nodes: dict[str, NodeInfo] = {}
        self._tasks: dict[str, InferenceTask] = {}
        self._task_queue: list[tuple[int, float, InferenceTask]] = []
        self._register_self()

    def register_node(self, node: NodeInfo) -> None:
        self._nodes[node.node_id] = node
        logger.info("Registered node %s at %s:%d", node.node_id, node.host, node.port)

    def unregister_node(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)

    def heartbeat(self, node_id: str, load: float = 0.0) -> bool:
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.last_heartbeat = time.time()
        node.current_load = load
        node.status = "healthy"
        return True

    def get_healthy_nodes(self) -> list[NodeInfo]:
        now = time.time()
        return [
            n for n in self._nodes.values()
            if n.status == "healthy" and now - n.last_heartbeat < 30.0
        ]

    def select_node(self, model_name: str, prefer_gpu_memory: bool = True) -> Optional[NodeInfo]:
        candidates = [
            n for n in self.get_healthy_nodes()
            if n.model_name == model_name or not model_name
        ]
        if not candidates:
            return None
        if prefer_gpu_memory:
            return max(candidates, key=lambda n: sum(g.get("memory_free", 0) for g in n.gpus))
        return min(candidates, key=lambda n: n.current_load)

    def submit_task(self, task: InferenceTask) -> None:
        self._tasks[task.task_id] = task
        import heapq
        heapq.heappush(self._task_queue, (-task.priority, task.created_at, task))

    def get_next_task(self, node_id: str) -> Optional[InferenceTask]:
        import heapq
        remaining: list[tuple[int, float, InferenceTask]] = []
        task = None
        while self._task_queue:
            _, _, candidate = heapq.heappop(self._task_queue)
            if candidate.node_id == node_id or candidate.node_id is None:
                task = candidate
                task.assigned_at = time.time()
                break
            remaining.append((_, _, candidate))
        self._task_queue = remaining + self._task_queue
        return task

    def complete_task(self, task_id: str, result: Any) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.result = result
            task.completed_at = time.time()

    def fail_task(self, task_id: str, error: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.error = error
            task.completed_at = time.time()

    def cluster_metrics(self) -> dict[str, Any]:
        healthy = self.get_healthy_nodes()
        total_capacity = sum(n.capacity for n in healthy)
        total_load = sum(n.current_load for n in healthy)
        return {
            "total_nodes": len(self._nodes),
            "healthy_nodes": len(healthy),
            "total_capacity": total_capacity,
            "total_load": total_load,
            "cluster_utilization": total_load / max(total_capacity, 1),
            "pending_tasks": len(self._task_queue),
        }

    def _register_self(self) -> None:
        node = NodeInfo(
            node_id=self.node_id,
            host=self.host,
            port=self.port,
            gpus=self.gpus,
            model_name="",
        )
        self._nodes[self.node_id] = node
