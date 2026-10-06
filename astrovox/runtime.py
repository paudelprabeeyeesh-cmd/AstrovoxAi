"""Thread pool and async scheduler for the Astrovox runtime.

Provides a bounded thread pool for CPU work and a lightweight async
scheduler so I/O and compute can be overlapped without adding heavy
external dependencies.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator


class ThreadPool:
    """Fixed-size worker pool with a FIFO task queue."""

    def __init__(self, workers: int = 4) -> None:
        self.workers = max(1, workers)
        self._queue: queue.Queue[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any], threading.Event]] = queue.Queue()
        self._threads: list[threading.Thread] = []
        self._shutdown = False
        for _ in range(self.workers):
            thread = threading.Thread(target=self._worker, daemon=True)
            thread.start()
            self._threads.append(thread)

    def _worker(self) -> None:
        while not self._shutdown:
            try:
                fn, args, kwargs, event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                fn(*args, **kwargs)
            finally:
                event.set()
                self._queue.task_done()

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> threading.Event:
        event = threading.Event()
        self._queue.put((fn, args, kwargs, event))
        return event

    def map(self, fn: Callable[..., Any], iterable: Iterable[Any]) -> list[Any]:
        events = [self.submit(fn, item) for item in iterable]
        for event in events:
            event.wait()
        return [fn(item) for item in iterable]

    def shutdown(self, wait: bool = True) -> None:
        self._shutdown = True
        if wait:
            self._queue.join()


class AsyncScheduler:
    """Minimal async-style scheduler over the thread pool."""

    def __init__(self, pool: ThreadPool | None = None) -> None:
        self.pool = pool or ThreadPool()

    def run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> threading.Event:
        return self.pool.submit(fn, *args, **kwargs)

    def wait_all(self, events: Iterable[threading.Event]) -> None:
        for event in events:
            event.wait()
