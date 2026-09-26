"""Task queue for background processing."""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import uuid


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    task_id: str
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskQueue:
    _queues: Dict[TaskPriority, asyncio.Queue] = {p: asyncio.Queue() for p in TaskPriority}
    _tasks: Dict[str, Task] = {}
    _handlers: Dict[str, Callable] = {}
    _running = False
    _workers: List[asyncio.Task] = []

    @classmethod
    async def enqueue(cls, task: Task) -> str:
        task.task_id = task.task_id or str(uuid.uuid4())
        task.status = TaskStatus.QUEUED
        cls._tasks[task.task_id] = task
        await cls._queues[task.priority].put(task)
        return task.task_id

    @classmethod
    async def dequeue(cls) -> Optional[Task]:
        for priority in sorted(TaskPriority, key=lambda p: p.value, reverse=True):
            queue = cls._queues[priority]
            if not queue.empty():
                return await queue.get()
        return None

    @classmethod
    async def process_task(cls, task: Task) -> None:
        handler = cls._handlers.get(task.name)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler for task: {task.name}"
            return
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task.payload)
            else:
                result = handler(task.payload)
            task.result = result
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
        task.completed_at = datetime.now(timezone.utc)

    @classmethod
    async def start_workers(cls, num_workers: int = 4) -> None:
        cls._running = True
        for _ in range(num_workers):
            worker = asyncio.create_task(cls._worker())
            cls._workers.append(worker)

    @classmethod
    async def _worker(cls) -> None:
        while cls._running:
            task = await cls.dequeue()
            if task:
                await cls.process_task(task)

    @classmethod
    async def stop_workers(cls) -> None:
        cls._running = False
        for worker in cls._workers:
            worker.cancel()

    @classmethod
    def register_handler(cls, task_name: str, handler: Callable) -> None:
        cls._handlers[task_name] = handler
