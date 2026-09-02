"""Distributed scheduler: DAG + priority queues + work stealing + leader."""

from __future__ import annotations

import asyncio
import heapq
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

from . import make_id, now
from ..logging_config import get_logger

logger = get_logger(__name__)


class JobState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    AWAITING_LEASE = "awaiting_lease"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    DEAD_LETTER = "dead_letter"


@dataclass
class Job:
    id: str
    name: str
    handler: Callable[["Job"], Awaitable[Dict[str, Any]]]
    depends_on: List[str] = field(default_factory=list)
    priority: int = 5
    timeout_seconds: float = 60.0
    max_retries: int = 0
    state: JobState = JobState.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attempts: int = 0
    resource_hint: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    scheduled_at: Optional[float] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    lease_id: Optional[str] = None
    lease_expires_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "depends_on": self.depends_on,
            "priority": self.priority,
            "state": self.state.value,
            "attempts": self.attempts,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "scheduled_at": self.scheduled_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "lease_id": self.lease_id,
            "lease_expires_at": self.lease_expires_at,
        }


class DistributedQueue:
    """Priority queue with work stealing."""

    def __init__(self) -> None:
        self._heap: List[Tuple[int, float, str, Job]] = []
        self._jobs: Dict[str, Job] = {}
        self._counter = 0

    def push(self, job: Job) -> None:
        self._counter += 1
        heapq.heappush(self._heap, (-job.priority, self._counter, job.id, job))
        self._jobs[job.id] = job
        job.scheduled_at = now()

    def pop(self) -> Optional[Job]:
        while self._heap:
            _, _, _, job = heapq.heappop(self._heap)
            if job.state in {JobState.PENDING, JobState.READY}:
                return job
        return None

    def steal(self, worker_id: str) -> Optional[Job]:
        job = self.pop()
        if job is not None:
            job.lease_id = worker_id
            job.lease_expires_at = now() + 30.0
        return job

    def release_lease(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or not job.lease_id:
            return False
        job.lease_id = None
        job.lease_expires_at = None
        self.push(job)
        return True

    def sweep_expired_leases(self) -> int:
        expired = 0
        for job in list(self._jobs.values()):
            if job.lease_id and job.lease_expires_at and job.lease_expires_at < now():
                job.lease_id = None
                job.lease_expires_at = None
                if job.state == JobState.RUNNING:
                    job.state = JobState.READY
                    self.push(job)
                    expired += 1
        return expired

    def stats(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = defaultdict(int)
        for job in self._jobs.values():
            by_state[job.state.value] += 1
        return {
            "queued": len(self._heap),
            "tracked": len(self._jobs),
            "by_state": dict(by_state),
        }


class Worker:
    def __init__(
        self,
        worker_id: str,
        queue: DistributedQueue,
        *,
        capacity: int = 4,
    ) -> None:
        self.id = worker_id
        self.queue = queue
        self.capacity = capacity
        self.active: List[Job] = []
        self.completed = 0
        self.failed = 0

    async def run_one(self, explicit_job: Optional[Job] = None) -> Optional[Job]:
        if len(self.active) >= self.capacity and explicit_job is None:
            return None
        job = explicit_job or self.queue.steal(self.id)
        if job is None:
            return None
        if explicit_job is not None:
            job.lease_id = self.id
            job.lease_expires_at = now() + 30.0
        job.state = JobState.RUNNING
        job.started_at = now()
        self.active.append(job)
        try:
            result = await asyncio.wait_for(job.handler(job), timeout=job.timeout_seconds)
            job.result = result if isinstance(result, dict) else {"value": result}
            job.state = JobState.SUCCEEDED
            job.finished_at = now()
            self.completed += 1
        except asyncio.TimeoutError:
            job.error = f"timeout after {job.timeout_seconds}s"
        except Exception as exc:
            job.error = str(exc)
        finally:
            if job.error and job.attempts < job.max_retries:
                job.attempts += 1
                job.state = JobState.READY
                self.queue.push(job)
            elif job.error:
                job.state = JobState.FAILED if job.attempts >= job.max_retries else JobState.READY
                if job.state == JobState.READY:
                    self.queue.push(job)
                else:
                    self.failed += 1
            self.active.remove(job)
        return job

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "capacity": self.capacity,
            "active": [j.to_dict() for j in self.active],
            "completed": self.completed,
            "failed": self.failed,
        }


class LeaderElector:
    """Lightweight leader election for a single AIOS cluster.

    A production deployment uses Raft or etcd; this implementation is
    appropriate for in-process testing and single-node leader handoff.
    """

    def __init__(self, ttl: float = 15.0) -> None:
        self._leader_id: Optional[str] = None
        self._expires_at: float = 0.0
        self._ttl = ttl
        self._epoch = 0

    def try_become_leader(self, candidate_id: str) -> bool:
        if self._leader_id and self._expires_at > now() and candidate_id != self._leader_id:
            return False
        self._leader_id = candidate_id
        self._epoch += 1
        self._expires_at = now() + self._ttl
        return True

    def leader(self) -> Optional[str]:
        if self._leader_id and self._expires_at > now():
            return self._leader_id
        return None

    def renew(self) -> bool:
        if self._leader_id is None:
            return False
        self._expires_at = now() + self._ttl
        return True

    def step_down(self) -> None:
        self._leader_id = None
        self._expires_at = 0.0

    def status(self) -> Dict[str, Any]:
        return {
            "leader": self.leader(),
            "epoch": self._epoch,
            "expires_at": self._expires_at,
        }


class DistributedScheduler:
    """DAG execution with leader election, work stealing, and retries."""

    def __init__(self, *, max_workers: int = 4, leader_ttl: float = 15.0) -> None:
        self.queue = DistributedQueue()
        self.workers: List[Worker] = [Worker(f"worker-{i}", self.queue) for i in range(max_workers)]
        self._leader = LeaderElector(ttl=leader_ttl)
        self._cancelled: set[str] = set()

    def submit(self, job: Job) -> Job:
        job.id = job.id or make_id("job")
        if job.depends_on:
            job.state = JobState.PENDING
        else:
            job.state = JobState.READY
        self.queue.push(job)
        return job

    def cancel(self, job_id: str) -> bool:
        self._cancelled.add(job_id)
        return True

    def leader_elect(self, candidate_id: str) -> bool:
        return self._leader.try_become_leader(candidate_id)

    def is_leader(self, candidate_id: str) -> bool:
        return self._leader.leader() == candidate_id

    async def run(self, deadline_s: float = 30.0) -> Dict[str, Any]:
        start = now()
        completed: List[str] = []
        failed: List[str] = []
        iteration = 0
        while now() - start < deadline_s:
            iteration += 1
            self.queue.sweep_expired_leases()
            # Skip ready jobs whose dependencies haven't finished.
            ready_jobs = [j for j in self.queue._jobs.values() if j.state == JobState.READY]
            progressed = False
            for job in ready_jobs:
                if job.depends_on and not all(
                    self.queue._jobs.get(d) and self.queue._jobs[d].state == JobState.SUCCEEDED
                    for d in job.depends_on
                ):
                    continue
                if job.id in self._cancelled:
                    job.state = JobState.CANCELLED
                    continue
                progressed = True
                await self._execute_on_any_worker(job)
                if job.state == JobState.SUCCEEDED:
                    completed.append(job.id)
                elif job.state == JobState.FAILED:
                    failed.append(job.id)
            if not progressed:
                # If nothing to do, exit early.
                if all(
                    j.state in {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED, JobState.SKIPPED}
                    for j in self.queue._jobs.values()
                ):
                    break
                await asyncio.sleep(0.05)
        return {
            "ok": not failed,
            "completed": completed,
            "failed": failed,
            "succeeded": len(completed),
            "failed_count": len(failed),
            "elapsed_s": round(now() - start, 3),
            "iterations": iteration,
            "queue": self.queue.stats(),
        }

    async def _execute_on_any_worker(self, job: Job) -> None:
        for worker in self.workers:
            if len(worker.active) < worker.capacity:
                await worker.run_one(explicit_job=job)
                return
        # All workers busy; try the first one anyway (capacity may have freed)
        await self.workers[0].run_one(explicit_job=job)

    def status(self) -> Dict[str, Any]:
        return {
            "queue": self.queue.stats(),
            "workers": [w.to_dict() for w in self.workers],
            "leader": self._leader.status(),
        }


_GLOBAL_SCHEDULER: Optional[DistributedScheduler] = None


def get_distributed_scheduler() -> DistributedScheduler:
    global _GLOBAL_SCHEDULER
    if _GLOBAL_SCHEDULER is None:
        _GLOBAL_SCHEDULER = DistributedScheduler()
    return _GLOBAL_SCHEDULER