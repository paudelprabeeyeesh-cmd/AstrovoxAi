"""Job scheduler with cron and delayed execution."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class JobState(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    job_id: str
    name: str
    func: Callable[..., Any]
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    cron: Optional[str] = None
    delay_seconds: Optional[float] = None
    state: JobState = JobState.PENDING
    result: Any = None
    error: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class JobScheduler:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._cron_jobs: Dict[str, Job] = {}

    def schedule_once(self, name: str, func: Callable[..., Any], delay_seconds: float, *args: Any, **kwargs: Any) -> Job:
        job_id = str(__import__("uuid").uuid4())
        job = Job(job_id=job_id, name=name, func=func, args=args, kwargs=kwargs, delay_seconds=delay_seconds, state=JobState.SCHEDULED)
        self._jobs[job_id] = job
        logger.info("Scheduled one-time job %s in %s seconds", name, delay_seconds)
        return job

    def schedule_cron(self, name: str, func: Callable[..., Any], cron: str, *args: Any, **kwargs: Any) -> Job:
        job_id = str(__import__("uuid").uuid4())
        job = Job(job_id=job_id, name=name, func=func, args=args, kwargs=kwargs, cron=cron, state=JobState.SCHEDULED)
        self._cron_jobs[job_id] = job
        self._jobs[job_id] = job
        logger.info("Scheduled cron job %s: %s", name, cron)
        return job

    async def run(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Unknown job: {job_id}")
        job.state = JobState.RUNNING
        try:
            result = job.func(*job.args, **job.kwargs)
            if hasattr(result, "__await__"):
                result = await result
            job.result = result
            job.state = JobState.COMPLETED
        except Exception as exc:
            job.error = str(exc)
            job.state = JobState.FAILED
            logger.exception("Job %s failed", job_id)
        job.completed_at = datetime.now(timezone.utc)
        return job

    def cancel(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.state = JobState.CANCELLED

    def list_jobs(self, state: Optional[JobState] = None) -> List[Dict[str, Any]]:
        jobs = list(self._jobs.values())
        if state:
            jobs = [j for j in jobs if j.state == state]
        return [
            {
                "job_id": j.job_id,
                "name": j.name,
                "state": j.state.value,
                "cron": j.cron,
                "error": j.error,
                "scheduled_at": j.scheduled_at.isoformat() if j.scheduled_at else None,
            }
            for j in jobs
        ]


job_scheduler = JobScheduler()
