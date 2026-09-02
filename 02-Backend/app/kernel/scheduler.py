"""Distributed workflow scheduler.

Implements DAG execution with priority queues, dependency resolution,
checkpointing, retries, and human approval gates.
"""

from __future__ import annotations

import asyncio
import heapq
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Sequence

from .bus import get_event_bus


class JobState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


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
    queued_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    approved: bool = False

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
            "queued_at": self.queued_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metadata": self.metadata,
            "requires_approval": self.requires_approval,
            "approved": self.approved,
        }


@dataclass
class Checkpoint:
    """Persisted snapshot of a job's run."""

    job_id: str
    state: JobState
    result: Optional[Dict[str, Any]]
    attempts: int
    captured_at: float = field(default_factory=time.time)


class DAG:
    """Lightweight DAG of jobs."""

    def __init__(self) -> None:
        self.jobs: Dict[str, Job] = {}
        self._adjacency: Dict[str, List[str]] = defaultdict(list)

    def add(self, job: Job) -> None:
        self.jobs[job.id] = job
        for dep in job.depends_on:
            self._adjacency[dep].append(job.id)

    def ready(self) -> List[Job]:
        ready: List[Job] = []
        for job in self.jobs.values():
            if job.state != JobState.PENDING:
                continue
            if job.requires_approval and not job.approved:
                continue
            if all(
                self.jobs.get(dep) is not None
                and self.jobs[dep].state == JobState.SUCCEEDED
                for dep in job.depends_on
            ):
                ready.append(job)
        return ready

    def is_done(self) -> bool:
        return all(
            j.state
            in {
                JobState.SUCCEEDED,
                JobState.FAILED,
                JobState.CANCELLED,
                JobState.SKIPPED,
            }
            for j in self.jobs.values()
        )

    def has_failures(self) -> bool:
        return any(j.state == JobState.FAILED for j in self.jobs.values())

    def topological(self) -> List[str]:
        indegree: Dict[str, int] = {jid: 0 for jid in self.jobs}
        for job in self.jobs.values():
            for dep in job.depends_on:
                if dep in indegree:
                    indegree[job.id] = indegree.get(job.id, 0) + 1
        # Filter to actually-present deps only
        for job in self.jobs.values():
            indegree[job.id] = sum(1 for d in job.depends_on if d in self.jobs)
        queue = [j for j, d in indegree.items() if d == 0]
        order: List[str] = []
        while queue:
            current = queue.pop(0)
            order.append(current)
            for child in self._adjacency.get(current, []):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        return order


class WorkflowScheduler:
    """Executes DAGs with priority, parallelism, retries, and approvals."""

    def __init__(self, max_concurrency: int = 8) -> None:
        self._max_concurrency = max_concurrency
        self._sem = asyncio.Semaphore(max_concurrency)
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._dag: Optional[DAG] = None
        self._cancelled: set[str] = set()

    # ----- DAG management ---------------------------------------------

    def load(self, dag: DAG) -> None:
        self._dag = dag
        get_event_bus().publish("workflow.loaded", {"jobs": len(dag.jobs)})

    def approve(self, job_id: str) -> bool:
        if not self._dag:
            return False
        job = self._dag.jobs.get(job_id)
        if not job:
            return False
        job.approved = True
        if job.state == JobState.AWAITING_APPROVAL:
            job.state = JobState.PENDING
        return True

    def cancel(self, job_id: str) -> bool:
        if not self._dag:
            return False
        job = self._dag.jobs.get(job_id)
        if not job:
            return False
        job.state = JobState.CANCELLED
        self._cancelled.add(job_id)
        return True

    def checkpoint(self, job_id: str) -> Optional[Checkpoint]:
        if not self._dag:
            return None
        job = self._dag.jobs.get(job_id)
        if not job:
            return None
        cp = Checkpoint(
            job_id=job_id,
            state=job.state,
            result=job.result,
            attempts=job.attempts,
        )
        self._checkpoints[job_id] = cp
        return cp

    def restore(self, job_id: str) -> Optional[Checkpoint]:
        return self._checkpoints.get(job_id)

    # ----- execution --------------------------------------------------

    async def run(self) -> Dict[str, Any]:
        if not self._dag:
            return {"ok": False, "error": "no DAG loaded"}
        dag = self._dag
        remaining: Dict[str, Job] = dict(dag.jobs)
        completed: List[str] = []
        failed: List[str] = []
        # Track jobs that are waiting on approval to break out of the loop.
        waiting_for_approval: set[str] = set()
        # Bound the outer loop to avoid infinite waits.
        max_iterations = len(dag.jobs) * 4 + 16
        iteration = 0

        async def _runner(job: Job) -> None:
            async with self._sem:
                if job.id in self._cancelled:
                    job.state = JobState.CANCELLED
                    return
                if job.requires_approval and not job.approved:
                    job.state = JobState.AWAITING_APPROVAL
                    return
                job.state = JobState.RUNNING
                job.started_at = time.time()
                get_event_bus().publish("workflow.job.started", {"id": job.id, "name": job.name})
                while job.attempts <= job.max_retries:
                    job.attempts += 1
                    try:
                        result = await asyncio.wait_for(job.handler(job), timeout=job.timeout_seconds)
                        job.result = result if isinstance(result, dict) else {"value": result}
                        job.state = JobState.SUCCEEDED
                        job.finished_at = time.time()
                        get_event_bus().publish(
                            "workflow.job.succeeded",
                            {"id": job.id, "name": job.name, "attempts": job.attempts},
                        )
                        return
                    except asyncio.TimeoutError:
                        job.error = f"timeout after {job.timeout_seconds}s"
                    except Exception as exc:
                        job.error = str(exc)
                job.state = JobState.FAILED
                job.finished_at = time.time()
                get_event_bus().publish(
                    "workflow.job.failed",
                    {"id": job.id, "name": job.name, "error": job.error},
                )

        while remaining and iteration < max_iterations:
            iteration += 1
            ready = [
                job
                for job in remaining.values()
                if all(dep in completed for dep in job.depends_on)
                and not (job.requires_approval and not job.approved)
            ]
            if not ready:
                waiting = [
                    j
                    for j in remaining.values()
                    if j.requires_approval and not j.approved
                ]
                # Mark any job whose deps failed/skipped as skipped.
                for j in list(remaining.values()):
                    if any(
                        dag.jobs[dep].state in {JobState.FAILED, JobState.SKIPPED}
                        for dep in j.depends_on
                        if dep in dag.jobs
                    ):
                        j.state = JobState.SKIPPED
                        remaining.pop(j.id, None)
                if not waiting:
                    break
                # Record and exit so callers can approve and re-run.
                waiting_for_approval = {j.id for j in waiting}
                break
            ready.sort(key=lambda j: j.priority, reverse=True)
            tasks = [asyncio.create_task(_runner(j)) for j in ready]
            for j in ready:
                remaining.pop(j.id, None)
            await asyncio.gather(*tasks, return_exceptions=True)
            for j in ready:
                if j.state == JobState.SUCCEEDED:
                    completed.append(j.id)
                elif j.state == JobState.FAILED:
                    failed.append(j.id)
                    for downstream in dag._adjacency.get(j.id, []):
                        ds = dag.jobs.get(downstream)
                        if ds and ds.state == JobState.PENDING:
                            ds.state = JobState.SKIPPED

        return {
            "ok": not failed and not waiting_for_approval,
            "completed": completed,
            "failed": failed,
            "awaiting_approval": sorted(waiting_for_approval),
            "succeeded": len(completed),
            "failed_count": len(failed),
            "total": len(dag.jobs),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


_GLOBAL_SCHEDULER: Optional[WorkflowScheduler] = None


def get_workflow_scheduler() -> WorkflowScheduler:
    global _GLOBAL_SCHEDULER
    if _GLOBAL_SCHEDULER is None:
        _GLOBAL_SCHEDULER = WorkflowScheduler()
    return _GLOBAL_SCHEDULER