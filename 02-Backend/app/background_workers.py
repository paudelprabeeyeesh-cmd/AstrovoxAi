"""Background workers for async processing with task submission, polling, and cancellation."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import uuid

logger = logging.getLogger("astravox.workers")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkerTask:
    task_id: str
    worker_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = TaskStatus.PENDING.value
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    _cancel_event: Optional[asyncio.Event] = field(default=None, repr=False, compare=False)

    def is_cancelled(self) -> bool:
        return self._cancel_event is not None and self._cancel_event.is_set()


class BackgroundWorker:
    """Async background worker pool with task submission, polling, and cancellation."""

    _workers: Dict[str, asyncio.Task] = {}
    _task_queue: asyncio.Queue = asyncio.Queue()
    _results: Dict[str, WorkerTask] = {}
    _running = False
    _lock = asyncio.Lock()
    _registry: Dict[str, WorkerTask] = {}

    @classmethod
    async def start(cls, num_workers: int = 4) -> None:
        async with cls._lock:
            if cls._running:
                return
            cls._running = True
            for i in range(num_workers):
                worker_id = f"worker-{i}"
                task = asyncio.create_task(cls._worker_loop(worker_id))
                cls._workers[worker_id] = task

    @classmethod
    async def _worker_loop(cls, worker_id: str) -> None:
        while cls._running:
            task: WorkerTask = await cls._task_queue.get()
            task.worker_id = worker_id
            task.status = TaskStatus.RUNNING.value
            task.started_at = datetime.now(timezone.utc)
            cls._registry[task.task_id] = task

            try:
                result = await cls._execute_task(task)
                task.result = result
                task.status = TaskStatus.COMPLETED.value
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED.value
                task.error = "Task was cancelled"
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED.value
            finally:
                task.completed_at = datetime.now(timezone.utc)
                cls._results[task.task_id] = task

    @classmethod
    async def _execute_task(cls, task: WorkerTask) -> Any:
        """Execute a task's payload function or default to ack completion."""
        func = task.payload.get("_func")
        if callable(func):
            return await func(task.payload)
        return "completed"

    @classmethod
    async def submit(cls, payload: Dict[str, Any]) -> str:
        task_id = str(uuid.uuid4())
        cancel_event = asyncio.Event()
        task = WorkerTask(
            task_id=task_id,
            worker_id="",
            payload=payload,
            _cancel_event=cancel_event,
        )
        await cls._task_queue.put(task)
        return task_id

    @classmethod
    def get_result(cls, task_id: str) -> Optional[WorkerTask]:
        return cls._results.get(task_id)

    @classmethod
    def get_results(cls, limit: int = 50) -> List[WorkerTask]:
        items = list(cls._results.values())
        items.sort(key=lambda t: t.created_at, reverse=True)
        return items[:limit]

    @classmethod
    def cancel(cls, task_id: str) -> bool:
        task = cls._registry.get(task_id)
        if task is None or task.status != TaskStatus.RUNNING.value:
            return False
        if task._cancel_event is not None:
            task._cancel_event.set()
            task.status = TaskStatus.CANCELLED.value
            task.error = "Task was cancelled"
            task.completed_at = datetime.now(timezone.utc)
            cls._results[task_id] = task
            logger.info("Task %s cancelled", task_id)
            return True
        return False

    @classmethod
    async def stop(cls) -> None:
        cls._running = False
        for worker in cls._workers.values():
            worker.cancel()
        if cls._workers:
            await asyncio.gather(*cls._workers.values(), return_exceptions=True)
        cls._workers.clear()
