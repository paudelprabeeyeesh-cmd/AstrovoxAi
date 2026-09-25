"""Distributed worker cluster: registration, leasing, failover, heartbeats."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from . import make_id, now
from ..logging_config import get_logger

logger = get_logger(__name__)


class WorkerState(str, Enum):
    STARTING = "starting"
    IDLE = "idle"
    BUSY = "busy"
    DRAINING = "draining"
    DEAD = "dead"


@dataclass
class Worker:
    id: str
    name: str
    address: str = "localhost"
    capacity: int = 4
    state: WorkerState = WorkerState.STARTING
    last_heartbeat: float = field(default_factory=now)
    active_jobs: Set[str] = field(default_factory=set)
    completed: int = 0
    failed: int = 0
    zone: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "capacity": self.capacity,
            "state": self.state.value,
            "last_heartbeat": self.last_heartbeat,
            "active_jobs": list(self.active_jobs),
            "completed": self.completed,
            "failed": self.failed,
            "zone": self.zone,
            "metadata": self.metadata,
        }


class WorkerRegistry:
    """In-process worker registry with heartbeats and failover detection."""

    HEARTBEAT_TIMEOUT = 30.0

    def __init__(self) -> None:
        self._workers: Dict[str, Worker] = {}
        self._by_name: Dict[str, List[str]] = defaultdict(list)
        self._listeners: List[Callable[[Worker, str], None]] = []

    def register(self, worker: Worker) -> Worker:
        worker.id = worker.id or make_id("worker")
        worker.state = WorkerState.IDLE
        worker.last_heartbeat = now()
        self._workers[worker.id] = worker
        self._by_name[worker.name].append(worker.id)
        self._emit(worker, "registered")
        return worker

    def deregister(self, worker_id: str) -> Optional[Worker]:
        worker = self._workers.pop(worker_id, None)
        if worker is None:
            return None
        self._by_name[worker.name] = [wid for wid in self._by_name[worker.name] if wid != worker_id]
        self._emit(worker, "deregistered")
        return worker

    def heartbeat(self, worker_id: str) -> bool:
        worker = self._workers.get(worker_id)
        if not worker:
            return False
        worker.last_heartbeat = now()
        if worker.state == WorkerState.STARTING:
            worker.state = WorkerState.IDLE
        return True

    def pick(self, name: Optional[str] = None) -> Optional[Worker]:
        candidates: List[Worker] = []
        for worker in self._workers.values():
            if worker.state not in {WorkerState.IDLE, WorkerState.BUSY}:
                continue
            if len(worker.active_jobs) >= worker.capacity:
                continue
            if worker.state == WorkerState.DRAINING:
                continue
            if name and worker.name != name:
                continue
            candidates.append(worker)
        if not candidates:
            return None
        # Pick the worker with the lowest load.
        candidates.sort(key=lambda w: (len(w.active_jobs), w.last_heartbeat))
        return candidates[0]

    def mark_busy(self, worker_id: str, job_id: str) -> None:
        worker = self._workers.get(worker_id)
        if not worker:
            return
        worker.state = WorkerState.BUSY
        worker.active_jobs.add(job_id)

    def mark_idle(self, worker_id: str, job_id: str) -> None:
        worker = self._workers.get(worker_id)
        if not worker:
            return
        worker.active_jobs.discard(job_id)
        if not worker.active_jobs and worker.state != WorkerState.DRAINING:
            worker.state = WorkerState.IDLE

    def detect_dead(self) -> List[str]:
        dead = []
        for worker in list(self._workers.values()):
            if now() - worker.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                worker.state = WorkerState.DEAD
                dead.append(worker.id)
                self._emit(worker, "dead")
        return dead

    def rebalance(self) -> List[Dict[str, Any]]:
        """Move active jobs from dead workers back to the queue."""

        dead = self.detect_dead()
        rebalanced: List[Dict[str, Any]] = []
        for worker_id in dead:
            worker = self._workers.pop(worker_id, None)
            if worker is None:
                continue
            for job_id in worker.active_jobs:
                rebalanced.append({"job_id": job_id, "from_worker": worker_id})
        return rebalanced

    def list(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self._workers.values()]

    def on_change(self, listener: Callable[[Worker, str], None]) -> None:
        self._listeners.append(listener)

    def _emit(self, worker: Worker, event: str) -> None:
        for listener in self._listeners:
            try:
                listener(worker, event)
            except Exception:
                continue

    def status(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = defaultdict(int)
        for worker in self._workers.values():
            by_state[worker.state.value] += 1
        return {
            "total": len(self._workers),
            "by_state": dict(by_state),
        }


_GLOBAL_REGISTRY: Optional[WorkerRegistry] = None


def get_worker_registry() -> WorkerRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = WorkerRegistry()
    return _GLOBAL_REGISTRY


def seed_default_workers() -> None:
    """Register a few logical workers for testing."""

    registry = get_worker_registry()
    if registry._workers:
        return
    for i in range(2):
        registry.register(
            Worker(
                id="",
                name=f"exec-worker-{i}",
                address=f"worker-{i}.local",
                capacity=4,
                zone="z1",
            )
        )