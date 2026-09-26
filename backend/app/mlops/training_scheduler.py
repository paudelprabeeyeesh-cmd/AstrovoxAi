"""Training scheduler for periodic and event-driven training jobs."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledJob:
    job_id: str
    name: str
    schedule: str
    func: Callable[[Dict[str, Any]], Any]
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.SCHEDULED
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class TrainingScheduler:
    def __init__(self) -> None:
        self._jobs: Dict[str, ScheduledJob] = {}

    def schedule(self, job: ScheduledJob) -> ScheduledJob:
        job.job_id = job.job_id or uuid.uuid4().hex
        self._jobs[job.job_id] = job
        return job

    async def run_job(self, job_id: str) -> Any:
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Unknown job: {job_id}")
        job.status = JobStatus.RUNNING
        job.last_run = datetime.now(timezone.utc)
        try:
            result = job.func(job.parameters)
            job.status = JobStatus.COMPLETED
            return result
        except Exception as exc:
            job.status = JobStatus.FAILED
            raise exc

    def get_jobs(self) -> List[ScheduledJob]:
        return list(self._jobs.values())


training_scheduler = TrainingScheduler()
