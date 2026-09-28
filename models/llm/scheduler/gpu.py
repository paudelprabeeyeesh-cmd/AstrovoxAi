"""GPU resource management for distributed scheduling."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class GPUResourceError(Exception):
    """Raised when GPU resources cannot satisfy a job."""


# ---------------------------------------------------------------------------
# Health and utilization tracking
# ---------------------------------------------------------------------------
class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class GPUStats:
    utilization_pct: float = 0.0
    memory_used_mb: int = 0
    memory_total_mb: int = 0
    temperature_c: float = 0.0
    power_watts: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class GPUNode:
    node_id: str
    gpu_type: str = "unknown"
    gpu_index: int = 0
    memory_total_mb: int = 0
    stats: GPUStats = field(default_factory=GPUStats)
    health: HealthStatus = HealthStatus.UNKNOWN
    running_jobs: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id:
            self.node_id = str(uuid.uuid4())

    @property
    def memory_free_mb(self) -> int:
        return max(0, self.memory_total_mb - self.stats.memory_used_mb)

    @property
    def memory_pct(self) -> float:
        if self.memory_total_mb <= 0:
            return 0.0
        return (self.stats.memory_used_mb / self.memory_total_mb) * 100.0

    @property
    def is_available(self) -> bool:
        return self.health == HealthStatus.HEALTHY and self.memory_free_mb > 0

    def can_fit(self, required_mb: int) -> bool:
        return self.memory_free_mb >= required_mb

    def update_stats(self, stats: GPUStats) -> None:
        self.stats = stats
        if stats.temperature_c > 105.0:
            self.health = HealthStatus.UNHEALTHY
        elif stats.temperature_c > 95.0:
            self.health = HealthStatus.DEGRADED
        elif self.health != HealthStatus.UNHEALTHY:
            self.health = HealthStatus.HEALTHY

    def assign_job(self, job_id: str) -> None:
        if job_id in self.running_jobs:
            raise GPUResourceError(f"Job {job_id} already assigned to node {self.node_id}")
        self.running_jobs.add(job_id)

    def release_job(self, job_id: str) -> None:
        self.running_jobs.discard(job_id)

    def current_load_pct(self) -> float:
        if self.memory_total_mb <= 0:
            return 0.0
        return (len(self.running_jobs) / max(1, self.memory_total_mb / 1024)) * 100.0


# ---------------------------------------------------------------------------
# GPU pool
# ---------------------------------------------------------------------------
class GPUPool:
    def __init__(self) -> None:
        self._nodes: dict[str, GPUNode] = {}
        self._lock = __import__("threading").Lock()

    def add_node(self, node: GPUNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node
            logger.debug("Added GPU node %s", node.node_id)

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            node = self._nodes.pop(node_id, None)
            if node:
                for job_id in list(node.running_jobs):
                    node.release_job(job_id)
                logger.debug("Removed GPU node %s", node_id)

    def get_node(self, node_id: str) -> GPUNode | None:
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self) -> list[GPUNode]:
        with self._lock:
            return list(self._nodes.values())

    def find_available(self, required_mb: int, gpu_type: str | None = None) -> list[GPUNode]:
        candidates = []
        with self._lock:
            for node in self._nodes.values():
                if not node.is_available:
                    continue
                if gpu_type and node.gpu_type != gpu_type:
                    continue
                if not node.can_fit(required_mb):
                    continue
                candidates.append(node)
        candidates.sort(key=lambda n: (n.memory_pct, n.node_id))
        return candidates

    def best_fit(self, required_mb: int, gpu_type: str | None = None) -> GPUNode | None:
        candidates = self.find_available(required_mb, gpu_type)
        if not candidates:
            return None
        return candidates[0]

    def total_free_memory_mb(self) -> int:
        return sum(n.memory_free_mb for n in self._nodes.values() if n.is_available)

    def total_memory_mb(self) -> int:
        return sum(n.memory_total_mb for n in self._nodes.values())

    def healthy_nodes(self) -> list[GPUNode]:
        with self._lock:
            return [n for n in self._nodes.values() if n.health == HealthStatus.HEALTHY]

    def update_node_stats(self, node_id: str, stats: GPUStats) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.update_stats(stats)

    def __len__(self) -> int:
        with self._lock:
            return len(self._nodes)
