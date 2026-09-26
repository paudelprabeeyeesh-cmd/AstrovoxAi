"""Task queue with Redis/Celery support."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str
    name: str
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3


class TaskQueue:
    """Simple task queue with Redis backend."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register_handler(self, task_name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self._handlers[task_name] = handler

    def enqueue(self, task_name: str, payload: Dict[str, Any]) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            name=task_name,
            payload=payload,
        )
        self._tasks[task.id] = task
        logger.info(f"Enqueued task {task.id}: {task_name}")
        return task

    def execute(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if not task:
            raise KeyError(f"Task not found: {task_id}")
        handler = self._handlers.get(task.name)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler registered for task: {task.name}"
            return task
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow().isoformat()
        try:
            result = handler(task.payload)
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow().isoformat()
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.completed_at = datetime.utcnow().isoformat()
            logger.error(f"Task {task.id} failed: {exc}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        return False


_task_queue = TaskQueue()


def get_task_queue() -> TaskQueue:
    return _task_queue
