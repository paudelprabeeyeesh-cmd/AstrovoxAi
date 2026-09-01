"""Background Job Queue — production-grade job processing with retries, dead-letter, and monitoring."""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class JobPriority(Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class Job:
    id: str
    type: str
    payload: dict
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    retry_count: int = 0
    error: str = ""
    result: Any = None
    progress: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    next_retry_at: float = 0.0


JobHandler = Callable[[Job], Any]


class JobQueue:
    """Async job queue with priority scheduling and dead-letter support."""

    def __init__(self, max_workers: int = 4):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._jobs: dict[str, Job] = {}
        self._handlers: dict[str, JobHandler] = {}
        self._dead_letter: list[Job] = []
        self._max_workers = max_workers
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "dead_lettered": 0,
        }

    def register_handler(self, job_type: str, handler: JobHandler):
        """Register a handler for a job type."""
        self._handlers[job_type] = handler

    async def submit(
        self,
        job_type: str,
        payload: dict,
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
    ) -> str:
        """Submit a job to the queue."""
        job = Job(
            id=str(uuid.uuid4()),
            type=job_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
        )
        self._jobs[job.id] = job
        await self._queue.put((-priority.value, job.created_at, job.id))
        self._stats["submitted"] += 1
        return job.id

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending job."""
        job = self._jobs.get(job_id)
        if not job or job.status != JobStatus.PENDING:
            return False
        job.status = JobStatus.CANCELLED
        return True

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        job_type: str = "",
        limit: int = 50,
    ) -> list[Job]:
        """List jobs with optional filtering."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        if job_type:
            jobs = [j for j in jobs if j.type == job_type]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)[:limit]

    def get_dead_letter(self) -> list[Job]:
        """Get dead-lettered jobs."""
        return list(self._dead_letter)

    async def retry_dead_letter(self, job_id: str) -> bool:
        """Retry a dead-lettered job."""
        for job in self._dead_letter:
            if job.id == job_id:
                job.status = JobStatus.PENDING
                job.retry_count = 0
                job.error = ""
                self._dead_letter.remove(job)
                await self._queue.put((-job.priority.value, job.created_at, job.id))
                return True
        return False

    async def start(self):
        """Start worker tasks."""
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self._max_workers)
        ]

    async def stop(self):
        """Stop all workers."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()

    async def _worker(self, worker_id: int):
        """Worker loop that processes jobs."""
        while self._running:
            try:
                _, _, job_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                continue

            job = self._jobs.get(job_id)
            if not job or job.status != JobStatus.PENDING:
                continue

            handler = self._handlers.get(job.type)
            if not handler:
                job.status = JobStatus.FAILED
                job.error = f"No handler for job type: {job.type}"
                self._stats["failed"] += 1
                continue

            job.status = JobStatus.RUNNING
            job.started_at = time.time()

            try:
                result = await handler(job)
                job.result = result
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                job.progress = 100
                self._stats["completed"] += 1
            except Exception as e:
                job.retry_count += 1
                job.error = str(e)[:500]

                if job.retry_count >= job.max_retries:
                    job.status = JobStatus.DEAD_LETTER
                    self._dead_letter.append(job)
                    self._stats["dead_lettered"] += 1
                else:
                    job.status = JobStatus.PENDING
                    delay = 2 ** job.retry_count
                    job.next_retry_at = time.time() + delay
                    await asyncio.sleep(delay)
                    await self._queue.put((-job.priority.value, job.created_at, job.id))

                self._stats["failed"] += 1

    def get_stats(self) -> dict:
        """Get queue statistics."""
        return {
            **self._stats,
            "pending": sum(1 for j in self._jobs.values() if j.status == JobStatus.PENDING),
            "running": sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING),
            "dead_letter_count": len(self._dead_letter),
            "total_jobs": len(self._jobs),
            "max_workers": self._max_workers,
        }


# Global job queue
job_queue = JobQueue()
