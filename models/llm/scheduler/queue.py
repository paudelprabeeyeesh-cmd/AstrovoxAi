"""Job queue with priority, fair sharing, and preemption."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from heapq import heappop, heappush
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------
class JobPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BEST_EFFORT = "best_effort"


_PRIORITY_WEIGHT: dict[JobPriority, int] = {
    JobPriority.CRITICAL: 0,
    JobPriority.HIGH: 1,
    JobPriority.NORMAL: 2,
    JobPriority.LOW: 3,
    JobPriority.BEST_EFFORT: 4,
}


class JobStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PREEMPTED = "preempted"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=False)
class Job:
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    required_gpus: int = 1
    required_memory_mb: int = 0
    max_runtime_seconds: float = 0.0
    tenant_id: str = "default"
    preemptible: bool = False
    created_at: float = field(default_factory=time.time)
    scheduled_at: float | None = None
    started_at: float | None = None
    finished_at: float | None = None
    assigned_node: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.job_id:
            self.job_id = str(uuid.uuid4())

    def _scheduling_key(self) -> tuple[int, float]:
        return (_PRIORITY_WEIGHT.get(self.priority, 2), self.created_at)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Job):
            return NotImplemented
        return self._scheduling_key() < other._scheduling_key()

    def runtime_seconds(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.finished_at or time.time()
        return end - self.started_at

    def is_terminal(self) -> bool:
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )


# ---------------------------------------------------------------------------
# Preemption policy
# ---------------------------------------------------------------------------
class PreemptionPolicy(StrEnum):
    NONE = "none"
    LOWEST_PRIORITY_FIRST = "lowest_priority_first"
    OLDEST_FIRST = "oldest_first"
    SHORTEST_JOB_FIRST = "shortest_job_first"


# ---------------------------------------------------------------------------
# Job queue
# ---------------------------------------------------------------------------
class JobQueue:
    def __init__(self) -> None:
        self._queue: list[Job] = []
        self._by_id: dict[str, Job] = {}
        self._lock = threading.Lock()

    def enqueue(self, job: Job) -> Job:
        with self._lock:
            job.status = JobStatus.QUEUED
            self._by_id[job.job_id] = job
            heappush(self._queue, job)
            logger.debug("Enqueued job %s", job.job_id)
            return job

    def dequeue(self) -> Job | None:
        with self._lock:
            while self._queue:
                job = heappop(self._queue)
                if self._by_id.get(job.job_id) is not job:
                    continue
                if job.is_terminal():
                    self._by_id.pop(job.job_id, None)
                    continue
                return job
            return None

    def peek(self) -> Job | None:
        with self._lock:
            if not self._queue:
                return None
            job = self._queue[0]
            return job if self._by_id.get(job.job_id) is job else None

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._by_id.get(job_id)

    def remove(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._by_id.pop(job_id, None)
            if job is None:
                return None
            try:
                self._queue.remove(job)
            except ValueError:
                pass
            return job

    def running_jobs(self) -> list[Job]:
        with self._lock:
            return [j for j in self._by_id.values() if j.status == JobStatus.RUNNING]

    def pending_jobs(self) -> list[Job]:
        with self._lock:
            return [j for j in self._by_id.values() if j.status in (JobStatus.PENDING, JobStatus.QUEUED)]

    def jobs_by_tenant(self, tenant_id: str) -> list[Job]:
        with self._lock:
            return [j for j in self._by_id.values() if j.tenant_id == tenant_id]

    def update_status(self, job_id: str, status: JobStatus) -> Job | None:
        job = self.get(job_id)
        if job is None:
            return None
        job.status = status
        if status == JobStatus.SCHEDULED:
            job.scheduled_at = time.time()
        elif status == JobStatus.RUNNING:
            job.started_at = time.time()
            job.status = JobStatus.RUNNING
        elif status == JobStatus.COMPLETED:
            job.finished_at = time.time()
        elif status in (JobStatus.FAILED, JobStatus.CANCELLED):
            job.finished_at = time.time()
        return job

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_id)


# ---------------------------------------------------------------------------
# Fair share scheduler
# ---------------------------------------------------------------------------
@dataclass
class TenantQuota:
    tenant_id: str
    max_parallel_jobs: int = 4
    max_memory_mb: int = 0
    reserved_gpus: int = 0


class FairShareScheduler:
    def __init__(self, queue: JobQueue, default_quota: TenantQuota | None = None) -> None:
        self._queue = queue
        self._default_quota = default_quota or TenantQuota(tenant_id="default")
        self._quotas: dict[str, TenantQuota] = {}
        self._active: dict[str, set[str]] = {}

    def set_quota(self, quota: TenantQuota) -> None:
        self._quotas[quota.tenant_id] = quota

    def get_quota(self, tenant_id: str) -> TenantQuota:
        return self._quotas.get(tenant_id, self._default_quota)

    def active_jobs(self, tenant_id: str) -> set[str]:
        return self._active.get(tenant_id, set())

    def can_schedule(self, job: Job) -> bool:
        quota = self.get_quota(job.tenant_id)
        current = len(self._active.get(job.tenant_id, set()))
        if current >= quota.max_parallel_jobs:
            return False
        return True

    def record_scheduled(self, job: Job) -> None:
        tenant = job.tenant_id
        if tenant not in self._active:
            self._active[tenant] = set()
        self._active[tenant].add(job.job_id)

    def record_finished(self, job: Job) -> None:
        tenant = job.tenant_id
        if tenant in self._active:
            self._active[tenant].discard(job.job_id)

    def next_queued(self, policy: PreemptionPolicy = PreemptionPolicy.NONE) -> Job | None:
        candidates = self._queue.pending_jobs()
        if not candidates:
            return None
        candidates.sort(key=lambda j: (_PRIORITY_WEIGHT.get(j.priority, 2), j.created_at))
        for job in candidates:
            if self.can_schedule(job):
                return job
        return None

    def preemptible_jobs(self, policy: PreemptionPolicy, required_gpus: int) -> list[Job]:
        if policy == PreemptionPolicy.NONE:
            return []
        candidates = self._queue.running_jobs()
        eligible = [j for j in candidates if j.preemptible]
        if policy == PreemptionPolicy.LOWEST_PRIORITY_FIRST:
            eligible.sort(key=lambda j: (_PRIORITY_WEIGHT.get(j.priority, 2), j.created_at))
        elif policy == PreemptionPolicy.OLDEST_FIRST:
            eligible.sort(key=lambda j: j.created_at)
        elif policy == PreemptionPolicy.SHORTEST_JOB_FIRST:
            eligible.sort(
                key=lambda j: (j.runtime_seconds() or float("inf"), j.created_at)
            )
        return eligible[:required_gpus]
