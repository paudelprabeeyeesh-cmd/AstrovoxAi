"""Task scheduler: priority queue with scheduling and execution."""

from __future__ import annotations

import asyncio
import heapq
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class ScheduledTask:
    """A scheduled task keyed by (priority, sequence)."""
    sort_key: tuple[float, float]
    id: str = field(compare=False)
    priority: int = field(compare=False)
    sequence: int = field(compare=False)
    description: str = field(compare=False)
    fn: Callable = field(compare=False)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    state: TaskState = field(compare=False, default=TaskState.PENDING)
    result: Any = field(compare=False, default=None)
    error: str | None = field(compare=False, default=None)
    scheduled_at: float = field(compare=False, default_factory=lambda: asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else __import__('time').time())


class TaskScheduler:
    """Priority scheduler for agent tasks."""

    def __init__(self, concurrency: int = 4):
        self.concurrency = concurrency
        self._heap: list[ScheduledTask] = []
        self._counter = 0
        self._running = False
        self._lock = asyncio.Lock()
        self._tasks: dict[str, ScheduledTask] = {}
        self._sem = asyncio.Semaphore(concurrency)

    def schedule(self, fn: Callable, *args, priority: int = 5,
                 **kwargs) -> str:
        self._counter += 1
        task = ScheduledTask(
            sort_key=(-priority, self._counter),
            id=str(uuid.uuid4())[:8], priority=priority, sequence=self._counter,
            description=fn.__name__, fn=fn, args=args, kwargs=kwargs
        )
        heapq.heappush(self._heap, task)
        self._tasks[task.id] = task
        return task.id

    async def _run(self, task: ScheduledTask) -> None:
        async with self._sem:
            task.state = TaskState.RUNNING
            try:
                task.result = task.fn(*task.args, **task.kwargs)
                task.state = TaskState.COMPLETED
            except Exception as e:
                task.error = str(e)
                task.state = TaskState.FAILED

    async def run_all(self) -> list[ScheduledTask]:
        """Run all pending tasks respecting priority order."""
        results = []
        async with self._lock:
            pending = []
            while self._heap:
                task = heapq.heappop(self._heap)
                if task.state == TaskState.CANCELLED:
                    continue
                task.state = TaskState.PENDING
                pending.append(task)
        await asyncio.gather(*[self._run(t) for t in pending])
        for t in pending:
            self._tasks[t.id] = t
            results.append(t)
        return sorted(results, key=lambda t: t.sort_key)

    def get(self, task_id: str) -> ScheduledTask | None:
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is not None and task.state == TaskState.PENDING:
            task.state = TaskState.CANCELLED
            return True
        return False

    def stats(self) -> dict:
        return {"pending": sum(1 for t in self._tasks.values() if t.state == TaskState.PENDING),
                "running": sum(1 for t in self._tasks.values() if t.state == TaskState.RUNNING),
                "completed": sum(1 for t in self._tasks.values() if t.state == TaskState.COMPLETED),
                "failed": sum(1 for t in self._tasks.values() if t.state == TaskState.FAILED)}


class Scheduler:
    """Synchronous wrapper around TaskScheduler for executor use."""

    def __init__(self, concurrency: int = 4):
        self._scheduler = TaskScheduler(concurrency=concurrency)

    def schedule(self, fn: Callable, *args, priority: int = 5, **kwargs) -> str:
        return self._scheduler.schedule(fn, *args, priority=priority, **kwargs)

    def run_all(self) -> list[ScheduledTask]:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(self._scheduler.run_all())

    def get(self, task_id: str) -> ScheduledTask | None:
        return self._scheduler.get(task_id)

    def cancel(self, task_id: str) -> bool:
        return self._scheduler.cancel(task_id)

    def stats(self) -> dict:
        return self._scheduler.stats()
