"""Scheduler for periodic tasks."""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import asyncio
import heapq


class ScheduleFrequency(Enum):
    ONCE = "once"
    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ScheduledTask:
    task_id: str
    name: str
    callback: Callable
    frequency: ScheduleFrequency
    next_run: datetime
    payload: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    last_run: Optional[datetime] = None
    run_count: int = 0


class Scheduler:
    _queue: List[tuple[datetime, str, ScheduledTask]] = []
    _tasks: Dict[str, ScheduledTask] = {}
    _running = False

    @classmethod
    def add_task(cls, task: ScheduledTask) -> str:
        heapq.heappush(cls._queue, (task.next_run, task.task_id, task))
        cls._tasks[task.task_id] = task
        return task.task_id

    @classmethod
    def remove_task(cls, task_id: str) -> None:
        cls._tasks.pop(task_id, None)

    @classmethod
    async def run(cls) -> None:
        cls._running = True
        while cls._running:
            if not cls._queue:
                await asyncio.sleep(1)
                continue
            next_run, task_id, task = cls._queue[0]
            now = datetime.now(timezone.utc)
            if next_run > now:
                await asyncio.sleep((next_run - now).total_seconds())
                continue
            heapq.heappop(cls._queue)
            if not task.active:
                continue
            try:
                if asyncio.iscoroutinefunction(task.callback):
                    await task.callback(**task.payload)
                else:
                    task.callback(**task.payload)
                task.last_run = datetime.now(timezone.utc)
                task.run_count += 1
                task.next_run = cls._calculate_next(task)
                heapq.heappush(cls._queue, (task.next_run, task.task_id, task))
            except Exception:
                pass

    @staticmethod
    def _calculate_next(task: ScheduledTask) -> datetime:
        now = datetime.now(timezone.utc)
        if task.frequency == ScheduleFrequency.MINUTELY:
            return now + timedelta(minutes=1)
        elif task.frequency == ScheduleFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif task.frequency == ScheduleFrequency.DAILY:
            return now + timedelta(days=1)
        elif task.frequency == ScheduleFrequency.WEEKLY:
            return now + timedelta(weeks=1)
        elif task.frequency == ScheduleFrequency.MONTHLY:
            return now + timedelta(days=30)
        return now + timedelta(days=1)

    @classmethod
    def start(cls) -> None:
        if not cls._running:
            asyncio.create_task(cls.run())

    @classmethod
    def stop(cls) -> None:
        cls._running = False
