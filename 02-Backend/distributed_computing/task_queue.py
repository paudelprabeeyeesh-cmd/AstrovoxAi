import heapq
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass(order=True)
class Task:
    priority: int
    task_id: str = field(compare=False)
    payload: Any = field(compare=False)
    created_at: float = field(default_factory=time.time, compare=False)
    retries: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)


class TaskQueue:
    def __init__(self) -> None:
        self._queue: List[Task] = []
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._closed = False

    def enqueue(self, task: Task) -> str:
        with self._cond:
            if self._closed:
                raise RuntimeError("Queue is closed")
            heapq.heappush(self._queue, task)
            self._cond.notify()
            return task.task_id

    def dequeue(self, timeout: Optional[float] = None) -> Optional[Task]:
        with self._cond:
            start = time.time()
            while not self._queue:
                if self._closed:
                    return None
                remaining = timeout
                if remaining is None:
                    self._cond.wait()
                else:
                    self._cond.wait(timeout=remaining)
                    if time.time() - start >= timeout:
                        return None
            return heapq.heappop(self._queue)

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()
