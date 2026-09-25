"""Background workers for async processing."""

from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import uuid


@dataclass
class WorkerTask:
    task_id: str
    worker_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BackgroundWorker:
    _workers: Dict[str, asyncio.Task] = {}
    _task_queue: asyncio.Queue = asyncio.Queue()
    _results: Dict[str, WorkerTask] = {}
    _running = False

    @classmethod
    async def start(cls, num_workers: int = 4) -> None:
        cls._running = True
        for i in range(num_workers):
            worker_id = f"worker-{i}"
            task = asyncio.create_task(cls._worker_loop(worker_id))
            cls._workers[worker_id] = task

    @classmethod
    async def _worker_loop(cls, worker_id: str) -> None:
        while cls._running:
            task = await cls._task_queue.get()
            task.worker_id = worker_id
            task.status = "running"
            try:
                task.result = "completed"
                task.status = "completed"
            except Exception as e:
                task.error = str(e)
                task.status = "failed"
            cls._results[task.task_id] = task

    @classmethod
    async def submit(cls, payload: Dict[str, Any]) -> str:
        task_id = str(uuid.uuid4())
        task = WorkerTask(task_id=task_id, worker_id="", payload=payload)
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
    async def stop(cls) -> None:
        cls._running = False
        for worker in cls._workers.values():
            worker.cancel()
