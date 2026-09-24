import heapq
from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass(order=True)
class PriorityItem(Generic[T]):
    priority: int
    item: T


class PriorityScheduler(Generic[T]):
    def __init__(self) -> None:
        self._queue: List[PriorityItem[T]] = []

    def add(self, priority: int, item: T) -> None:
        heapq.heappush(self._queue, PriorityItem(-priority, item))

    def next(self) -> Optional[T]:
        if not self._queue:
            return None
        return heapq.heappop(self._queue).item

    def __len__(self) -> int:
        return len(self._queue)
