"""ACDOS AI Compute Fabric: distributed execution graphs, worker orchestration,
GPU/CPU scheduling, queues, checkpoint migration, job recovery, multi-tenant.
"""

from __future__ import annotations

import asyncio
import heapq
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from . import make_id, now, now_iso
from .control_plane import ClusterCoordinator, Node, get_cluster_coordinator
from ..logging_config import get_logger

logger = get_logger(__name__)


class JobState(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    CHECKPOINTED = "checkpointed"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    MIGRATED = "migrated"
    DEAD_LETTER = "dead_letter"


class Priority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class Checkpoint:
    job_id: str
    state: JobState
    result: Optional[Dict[str, Any]]
    captured_at: float = field(default_factory=now)
    node_id: Optional[str] = None


@dataclass
class Job:
    id: str
    name: str
    tenant: str
    handler: Callable[["Job"], Awaitable[Any]]
    requirements: Dict[str, float] = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    state: JobState = JobState.PENDING
    attempts: int = 0
    max_retries: int = 0
    timeout_s: float = 60.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    assigned_node: Optional[str] = None
    queued_at: float = field(default_factory=now)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tenant": self.tenant,
            "state": self.state.value,
            "priority": int(self.priority),
            "attempts": self.attempts,
            "assigned_node": self.assigned_node,
            "queued_at": self.queued_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class PriorityQueue:
    def __init__(self) -> None:
        self._heap: List[Tuple[int, float, str, Job]] = []
        self._index: Dict[str, Job] = {}
        self._counter = 0

    def push(self, job: Job) -> None:
        self._counter += 1
        heapq.heappush(
            self._heap, (-int(job.priority), self._counter, job.id, job)
        )
        self._index[job.id] = job

    def pop(self) -> Optional[Job]:
        while self._heap:
            _, _, _, job = heapq.heappop(self._heap)
            if job.state in {JobState.PENDING, JobState.SCHEDULED}:
                return job
        return None

    def remove(self, job_id: str) -> bool:
        if job_id not in self._index:
            return False
        del self._index[job_id]
        return True

    def stats(self) -> Dict[str, int]:
        by_state: Dict[str, int] = defaultdict(int)
        for job in self._index.values():
            by_state[job.state.value] += 1
        return {
            "queued": len(self._heap),
            "tracked": len(self._index),
            "by_state": dict(by_state),
        }


class CheckpointStore:
    def __init__(self) -> None:
        self._checkpoints: Dict[str, List[Checkpoint]] = defaultdict(list)

    def save(self, checkpoint: Checkpoint) -> None:
        self._checkpoints[checkpoint.job_id].append(checkpoint)

    def latest(self, job_id: str) -> Optional[Checkpoint]:
        items = self._checkpoints.get(job_id)
        return items[-1] if items else None

    def list(self, job_id: str) -> List[Checkpoint]:
        return list(self._checkpoints.get(job_id, []))


class AIComputeFabric:
    """Distributed execution fabric with GPU/CPU scheduling and checkpointing."""

    def __init__(
        self,
        coordinator: Optional[ClusterCoordinator] = None,
        checkpoint_store: Optional[CheckpointStore] = None,
    ) -> None:
        self.coordinator = coordinator or get_cluster_coordinator()
        self.queue = PriorityQueue()
        self.checkpoints = checkpoint_store or CheckpointStore()
        self._jobs: Dict[str, Job] = {}
        self._workers: Dict[str, int] = {}
        self._tenants: Dict[str, int] = defaultdict(int)
        self._sem = asyncio.Semaphore(64)
        self._lock_proxy: List[Any] = []

    def submit(
        self,
        name: str,
        handler: Callable[[Job], Awaitable[Any]],
        *,
        tenant: str = "default",
        requirements: Optional[Dict[str, float]] = None,
        priority: Priority = Priority.NORMAL,
        max_retries: int = 0,
        timeout_s: float = 60.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Job:
        job = Job(
            id=make_id("job"),
            name=name,
            tenant=tenant,
            handler=handler,
            requirements=requirements or {},
            priority=priority,
            max_retries=max_retries,
            timeout_s=timeout_s,
            metadata=metadata or {},
        )
        self._jobs[job.id] = job
        self.queue.push(job)
        return job

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        job.state = JobState.CANCELLED
        return True

    def checkpoint_job(self, job_id: str) -> Optional[Checkpoint]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        cp = Checkpoint(
            job_id=job.id,
            state=job.state,
            result=job.result,
            node_id=job.assigned_node,
        )
        self.checkpoints.save(cp)
        return cp

    def migrate(self, job_id: str, target_node: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        cp = self.checkpoints.latest(job_id)
        if cp is None:
            return False
        job.assigned_node = target_node
        job.state = JobState.SCHEDULED
        self.queue.push(job)
        return True

    def _schedule_to(self, job: Job) -> Optional[str]:
        node = self.coordinator.schedule(
            job.requirements, zone=job.metadata.get("zone")
        )
        if node is None:
            return None
        if not self.coordinator.allocate(node.id, job.requirements):
            return None
        job.assigned_node = node.id
        self._workers[node.id] = self._workers.get(node.id, 0) + 1
        self._tenants[job.tenant] = self._tenants.get(job.tenant, 0) + 1
        return node.id

    def _release(self, job: Job) -> None:
        if job.assigned_node:
            self.coordinator.release(job.assigned_node, job.requirements)
            self._workers[job.assigned_node] = max(
                0, self._workers.get(job.assigned_node, 0) - 1
            )
            self._tenants[job.tenant] = max(
                0, self._tenants.get(job.tenant, 0) - 1
            )

    async def run(self, deadline_s: float = 30.0) -> Dict[str, Any]:
        start = now()
        completed: List[str] = []
        failed: List[str] = []
        cancelled: List[str] = []
        iteration = 0
        max_iterations = max(8, len(self._jobs) * 4)

        while now() - start < deadline_s and iteration < max_iterations:
            iteration += 1
            self.coordinator.detect_dead()
            # Rebalance jobs assigned to dead nodes
            for job in list(self._jobs.values()):
                if (
                    job.state in {JobState.RUNNING, JobState.SCHEDULED}
                    and job.assigned_node
                    and not self.coordinator.heartbeat(job.assigned_node)
                ):
                    self.migrate(job.id, target_node=job.assigned_node)
            ready = [
                j
                for j in self.queue._index.values()
                if j.state in {JobState.PENDING, JobState.SCHEDULED}
            ]
            ready.sort(key=lambda j: -int(j.priority))
            progressed = False
            for job in ready:
                node_id = self._schedule_to(job)
                if node_id is None:
                    continue
                progressed = True
                job.state = JobState.RUNNING
                job.started_at = now()
                try:
                    result = await asyncio.wait_for(
                        job.handler(job), timeout=job.timeout_s
                    )
                    job.result = result if isinstance(result, dict) else {"value": result}
                    job.state = JobState.SUCCEEDED
                    job.finished_at = now()
                    completed.append(job.id)
                except asyncio.TimeoutError:
                    job.error = f"timeout after {job.timeout_s}s"
                except Exception as exc:
                    job.error = str(exc)
                if job.error:
                    if job.attempts < job.max_retries:
                        job.attempts += 1
                        job.state = JobState.SCHEDULED
                        self.queue.push(job)
                    else:
                        job.state = JobState.FAILED
                        job.finished_at = now()
                        failed.append(job.id)
                self._release(job)
            if not progressed:
                if all(
                    j.state
                    in {
                        JobState.SUCCEEDED,
                        JobState.FAILED,
                        JobState.CANCELLED,
                        JobState.DEAD_LETTER,
                    }
                    for j in self._jobs.values()
                ):
                    break
                await asyncio.sleep(0.01)
        return {
            "ok": not failed and not cancelled,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "elapsed_s": round(now() - start, 3),
            "iterations": iteration,
            "queue": self.queue.stats(),
        }

    def status(self) -> Dict[str, Any]:
        return {
            "queue": self.queue.stats(),
            "workers_by_node": dict(self._workers),
            "jobs_by_tenant": dict(self._tenants),
            "total_jobs": len(self._jobs),
        }


_GLOBAL_FABRIC: Optional[AIComputeFabric] = None


def get_compute_fabric() -> AIComputeFabric:
    global _GLOBAL_FABRIC
    if _GLOBAL_FABRIC is None:
        _GLOBAL_FABRIC = AIComputeFabric()
    return _GLOBAL_FABRIC