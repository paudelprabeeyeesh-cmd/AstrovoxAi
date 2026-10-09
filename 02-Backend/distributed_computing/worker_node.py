import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class WorkerNode:
    node_id: str
    max_workers: int = 4
    _active: int = field(default=0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if self._active >= self._max_workers:
                raise RuntimeError(f"Worker {self.node_id} is at capacity")
            self._active += 1
        try:
            return func(*args, **kwargs)
        finally:
            with self._lock:
                self._active -= 1

    def available(self) -> bool:
        with self._lock:
            return self._active < self._max_workers

    def active_count(self) -> int:
        with self._lock:
            return self._active
