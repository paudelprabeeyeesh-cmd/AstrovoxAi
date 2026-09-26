"""Backpressure handler for controlling throughput."""

import asyncio
import inspect
import logging
import threading
from typing import Any, AsyncIterator, Callable, List, Optional, TypeVar

logger = logging.getLogger("astrovox.backpressure")

T = TypeVar("T")


class BackpressureHandler:
    """Apply backpressure to limit in-flight work."""

    def __init__(self, max_concurrency: int = 10, queue_size: int = 100) -> None:
        self._max_concurrency = max_concurrency
        self._queue_size = queue_size
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._active = 0
        self._queued = 0
        self._rejected = 0
        self._lock = threading.Lock()

    async def initialize(self) -> None:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrency)

    async def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if self._semaphore is None:
            await self.initialize()
        async with self._semaphore:
            with self._lock:
                self._active += 1
            try:
                if inspect.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            finally:
                with self._lock:
                    self._active -= 1

    async def execute_stream(self, items: AsyncIterator[T], func: Callable[[T], Any]) -> AsyncIterator[Any]:
        if self._semaphore is None:
            await self.initialize()
        tasks: List[asyncio.Task] = []
        async for item in items:
            with self._lock:
                if self._queued >= self._queue_size:
                    self._rejected += 1
                    continue
                self._queued += 1
            task = asyncio.create_task(self._run(func, item))
            tasks.append(task)
            if len(tasks) >= self._queue_size:
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                tasks = list(pending)
                for t in done:
                    yield t.result()
        for task in tasks:
            yield await task

    async def _run(self, func: Callable[[T], Any], item: T) -> Any:
        try:
            return await self.execute(func, item)
        finally:
            with self._lock:
                self._queued -= 1

    @property
    def active_count(self) -> int:
        with self._lock:
            return self._active

    @property
    def queued_count(self) -> int:
        with self._lock:
            return self._queued

    @property
    def rejected_count(self) -> int:
        with self._lock:
            return self._rejected

    @property
    def max_concurrency(self) -> int:
        return self._max_concurrency

    @property
    def queue_size(self) -> int:
        return self._queue_size
