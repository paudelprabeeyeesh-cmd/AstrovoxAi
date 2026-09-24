import threading
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class ResourcePool(Generic[T]):
    def __init__(self, factory, size: int = 5) -> None:
        self._factory = factory
        self._size = size
        self._pool: list[T] = []
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        for _ in range(size):
            self._pool.append(factory())

    def acquire(self) -> Optional[T]:
        with self._cond:
            while not self._pool:
                self._cond.wait()
            return self._pool.pop()

    def release(self, resource: T) -> None:
        with self._cond:
            self._pool.append(resource)
            self._cond.notify()

    def available(self) -> int:
        with self._lock:
            return len(self._pool)
