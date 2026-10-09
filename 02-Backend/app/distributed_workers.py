"""Distributed worker orchestration for AstrovoxAI backend.

Provides worker pools, task routing, and result aggregation.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .distributed_queue import DistributedQueue, JobPriority, QueueJob

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    name: str
    concurrency: int = 4
    timeout: float = 30.0
    retry_delay: float = 1.0
    max_retries: int = 3


@dataclass
class WorkerResult:
    job_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class DistributedWorker:
    """Single worker that processes jobs from the distributed queue."""

    def __init__(self, config: WorkerConfig, queue: Optional[DistributedQueue] = None):
        self.config = config
        self.queue = queue or DistributedQueue()
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._handlers: Dict[str, Callable] = {}
        self._active_jobs: int = 0

    def register_handler(self, job_type: str, handler: Callable) -> None:
        self._handlers[job_type] = handler

    async def start(self, consumer_name: Optional[str] = None) -> None:
        self.running = True
        consumer = consumer_name or f"{self.config.name}-{uuid.uuid4().hex[:8]}"
        logger.info("Starting distributed worker %s with concurrency=%d", consumer, self.config.concurrency)
        self._task = asyncio.create_task(self._run(consumer))

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self, consumer_name: str) -> None:
        semaphore = asyncio.Semaphore(self.config.concurrency)
        while self.running:
            try:
                job = self.queue.dequeue(consumer_name=consumer_name, timeout_ms=1000)
                if job:
                    asyncio.create_task(self._process_job(job, semaphore))
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("Worker %s loop error: %s", self.config.name, exc)
                await asyncio.sleep(1.0)

    async def _process_job(self, job: QueueJob, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            self._active_jobs += 1
            start = time.perf_counter()
            handler = self._handlers.get(job.payload.get("type"))
            if not handler:
                self.queue.nack(job.job_id, f"No handler for type: {job.payload.get('type')}")
                self._active_jobs -= 1
                return
            try:
                result = await asyncio.wait_for(
                    asyncio.create_task(handler(job.payload)) if asyncio.iscoroutinefunction(handler)
                    else asyncio.to_thread(handler, job.payload),
                    timeout=self.config.timeout,
                )
                duration = (time.perf_counter() - start) * 1000
                logger.info("Job %s completed in %.2fms", job.job_id, duration)
                self._active_jobs -= 1
                return WorkerResult(
                    job_id=job.job_id,
                    success=True,
                    result=result,
                    duration_ms=duration,
                )
            except asyncio.TimeoutError:
                duration = (time.perf_counter() - start) * 1000
                logger.error("Job %s timed out after %.2fms", job.job_id, duration)
                self.queue.nack(job.job_id, "Job timed out")
            except Exception as exc:  # noqa: BLE001
                duration = (time.perf_counter() - start) * 1000
                logger.error("Job %s failed: %s", job.job_id, exc)
                self.queue.nack(job.job_id, str(exc))
            self._active_jobs -= 1
            return WorkerResult(
                job_id=job.job_id,
                success=False,
                error=str(exc),
                duration_ms=duration,
            )

    @property
    def active_jobs(self) -> int:
        return self._active_jobs


class DistributedWorkerPool:
    """Pool of distributed workers for parallel job processing."""

    def __init__(self, queue: Optional[DistributedQueue] = None):
        self.queue = queue or DistributedQueue()
        self._workers: List[DistributedWorker] = []
        self._tasks: List[asyncio.Task] = []

    def add_worker(self, config: WorkerConfig) -> DistributedWorker:
        worker = DistributedWorker(config, self.queue)
        self._workers.append(worker)
        return worker

    async def start_all(self) -> None:
        for worker in self._workers:
            await worker.start()

    async def stop_all(self) -> None:
        for worker in self._workers:
            await worker.stop()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "worker_count": len(self._workers),
            "active_jobs": sum(w.active_jobs for w in self._workers),
            "workers": [
                {
                    "name": w.config.name,
                    "concurrency": w.config.concurrency,
                    "active_jobs": w.active_jobs,
                }
                for w in self._workers
            ],
        }


worker_pool = DistributedWorkerPool()
