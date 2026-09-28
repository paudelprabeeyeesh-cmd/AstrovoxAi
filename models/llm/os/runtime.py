"""AI Operating System Runtime."""

import logging
import multiprocessing
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ProcessState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Process:
    pid: int
    name: str
    state: ProcessState = ProcessState.PENDING
    priority: int = 0
    resource_requirements: dict[str, Any] = None
    result: Any = None
    error: str | None = None

    def __post_init__(self):
        if self.resource_requirements is None:
            self.resource_requirements = {}


class ProcessManager:
    def __init__(self) -> None:
        self._processes: dict[int, Process] = {}
        self._next_pid = 1
        self._lock = threading.Lock()

    def spawn(self, name: str, fn: Callable, args: tuple = (), kwargs: dict | None = None, priority: int = 0) -> Process:
        kwargs = kwargs or {}
        with self._lock:
            pid = self._next_pid
            self._next_pid += 1
        proc = Process(pid=pid, name=name, priority=priority)
        self._processes[pid] = proc
        proc.state = ProcessState.RUNNING
        try:
            proc.result = fn(*args, **kwargs)
            proc.state = ProcessState.COMPLETED
        except Exception as exc:
            proc.state = ProcessState.FAILED
            proc.error = str(exc)
            logger.error("Process %d failed: %s", pid, exc)
        return proc

    def get(self, pid: int) -> Process:
        return self._processes[pid]

    def terminate(self, pid: int) -> None:
        proc = self._processes.get(pid)
        if proc:
            proc.state = ProcessState.FAILED
            logger.info("Terminated process %d", pid)

    def list_processes(self) -> list[Process]:
        return list(self._processes.values())


class ResourceAllocator:
    def __init__(self) -> None:
        self._available: dict[str, float] = {}
        self._allocated: dict[str, dict[str, float]] = {}

    def set_capacity(self, resource: str, amount: float) -> None:
        self._available[resource] = amount
        self._allocated.setdefault(resource, {})

    def request(self, owner: str, resource: str, amount: float) -> bool:
        if self._available.get(resource, 0) < amount:
            return False
        current = sum(self._allocated.get(resource, {}).values())
        if current + amount > self._available.get(resource, 0):
            return False
        self._allocated.setdefault(resource, {})[owner] = amount
        logger.debug("Allocated %.2f of %s to %s", amount, resource, owner)
        return True

    def release(self, owner: str, resource: str) -> None:
        if resource in self._allocated and owner in self._allocated[resource]:
            del self._allocated[resource][owner]

    def usage(self) -> dict[str, dict[str, Any]]:
        report: dict[str, dict[str, Any]] = {}
        for resource, total in self._available.items():
            used = sum(self._allocated.get(resource, {}).values())
            report[resource] = {
                "total": total,
                "used": used,
                "free": total - used,
            }
        return report


class Scheduler:
    def __init__(self) -> None:
        self._queue: list[tuple[int, Any]] = []
        self._results: dict[int, Any] = {}

    def submit(self, task_id: int, task: Any) -> None:
        self._queue.append((task_id, task))
        self._queue.sort(key=lambda x: x[0])

    def run_next(self) -> tuple[int, Any] | None:
        if not self._queue:
            return None
        task_id, task = self._queue.pop(0)
        try:
            result = task()
            self._results[task_id] = result
            return task_id, result
        except Exception as exc:
            logger.error("Task %d failed: %s", task_id, exc)
            return task_id, None

    def pending_count(self) -> int:
        return len(self._queue)

    def get_result(self, task_id: int) -> Any:
        return self._results.get(task_id)
