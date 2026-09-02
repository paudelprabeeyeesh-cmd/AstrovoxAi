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
    TIMED_OUT = "timed_out"
    DEAD_LETTER = "dead_letter"


class JobPriority(Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class BackoffStrategy(Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


@dataclass
class Job:
    id: str
    type: str
    payload: dict
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 300
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    error: str = ""
    result: Any = None
    progress: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    next_retry_at: float = 0.0
    worker_id: str = ""
    persistence_key: str = ""


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
            "timed_out": 0,
        }
        self._persistence_hooks: list[Callable[[Job], Any]] = []
        self._completion_hooks: list[Callable[[Job], Any]] = []

    def register_handler(self, job_type: str, handler: JobHandler):
        """Register a handler for a job type."""
        self._handlers[job_type] = handler

    def add_persistence_hook(self, hook: Callable[[Job], Any]):
        """Register a hook called on job state transitions for persistence."""
        self._persistence_hooks.append(hook)

    def add_completion_hook(self, hook: Callable[[Job], Any]):
        """Register a hook fired when a job completes (success/failure)."""
        self._completion_hooks.append(hook)

    async def submit(
        self,
        job_type: str,
        payload: dict,
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        persistence_key: str = "",
    ) -> str:
        """Submit a job to the queue."""
        job = Job(
            id=str(uuid.uuid4()),
            type=job_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            backoff_strategy=backoff_strategy,
            persistence_key=persistence_key,
        )
        self._jobs[job.id] = job
        await self._queue.put((-priority.value, job.created_at, job.id))
        self._stats["submitted"] += 1
        await self._fire_hooks(job)
        return job.id

    async def _fire_hooks(self, job: Job):
        """Fire persistence hooks for a job."""
        for hook in self._persistence_hooks:
            try:
                result = hook(job)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

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
        worker_tag = f"worker-{worker_id}"
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
                await self._fire_hooks(job)
                await self._fire_completion(job)
                continue

            job.status = JobStatus.RUNNING
            job.started_at = time.time()
            job.worker_id = worker_tag
            await self._fire_hooks(job)

            try:
                result = await asyncio.wait_for(handler(job), timeout=job.timeout_seconds)
                job.result = result
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                job.progress = 100
                self._stats["completed"] += 1
                await self._fire_hooks(job)
                await self._fire_completion(job)
            except asyncio.TimeoutError:
                job.retry_count += 1
                job.error = f"Timeout after {job.timeout_seconds}s"
                await self._handle_failure(job)
            except Exception as e:
                job.retry_count += 1
                job.error = str(e)[:500]
                await self._handle_failure(job)

    async def _handle_failure(self, job: Job):
        """Handle job failure with retry/backoff/dead-letter."""
        if job.retry_count >= job.max_retries:
            if job.error.startswith("Timeout"):
                job.status = JobStatus.DEAD_LETTER
                self._stats["timed_out"] += 1
            else:
                job.status = JobStatus.DEAD_LETTER
            self._dead_letter.append(job)
            self._stats["dead_lettered"] += 1
        else:
            job.status = JobStatus.PENDING
            delay = self._backoff_delay(job.backoff_strategy, job.retry_count)
            job.next_retry_at = time.time() + delay
            await asyncio.sleep(delay)
            await self._queue.put((-job.priority.value, job.created_at, job.id))

        self._stats["failed"] += 1
        await self._fire_hooks(job)
        await self._fire_completion(job)

    def _backoff_delay(self, strategy: BackoffStrategy, attempt: int) -> float:
        """Compute retry backoff based on strategy."""
        if strategy == BackoffStrategy.EXPONENTIAL:
            return float(2 ** attempt)
        if strategy == BackoffStrategy.LINEAR:
            return float(attempt + 1)
        return 1.0

    async def _fire_completion(self, job: Job):
        """Fire completion hooks."""
        for hook in self._completion_hooks:
            try:
                result = hook(job)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

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
