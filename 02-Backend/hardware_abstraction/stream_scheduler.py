from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from heapq import heappop, heappush
from typing import Any, Callable, Dict, List, Optional


class StreamStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class StreamTask:
    stream_id: str
    priority: StreamPriority
    payload: Any
    callback: Optional[Callable[[str], None]] = None


@dataclass(order=True)
class ScheduledItem:
    timestamp: float
    sequence: int
    stream_id: str = field(compare=False)
    priority: StreamPriority = field(compare=False)
    payload: Any = field(default=None, compare=False)
    callback: Optional[Callable[[str], None]] = field(default=None, compare=False)


class StreamScheduler:
    def __init__(self) -> None:
        self._queue: List[ScheduledItem] = []
        self._counter = 0
        self._streams: Dict[str, StreamStatus] = {}
        self._results: Dict[str, Any] = {}

    def _next_sequence(self) -> int:
        self._counter += 1
        return self._counter

    def submit(self, stream_id: str, priority: StreamPriority, payload: Any, callback: Optional[Callable[[str], None]] = None) -> None:
        item = ScheduledItem(
            timestamp=time.monotonic(),
            sequence=self._next_sequence(),
            stream_id=stream_id,
            priority=priority,
            payload=payload,
            callback=callback,
        )
        heappush(self._queue, item)
        self._streams[stream_id] = StreamStatus.PENDING

    def run_pending(self, limit: int = 10) -> List[str]:
        executed = []
        count = 0
        while self._queue and count < limit:
            item = heappop(self._queue)
            if self._streams.get(item.stream_id) == StreamStatus.COMPLETED:
                continue
            self._streams[item.stream_id] = StreamStatus.RUNNING
            self._results[item.stream_id] = item.payload
            self._streams[item.stream_id] = StreamStatus.COMPLETED
            if item.callback:
                item.callback(item.stream_id)
            executed.append(item.stream_id)
            count += 1
        return executed

    def cancel(self, stream_id: str) -> bool:
        if stream_id not in self._streams or self._streams[stream_id] == StreamStatus.COMPLETED:
            return False
        self._streams[stream_id] = StreamStatus.FAILED
        return True

    def status(self, stream_id: str) -> Optional[StreamStatus]:
        return self._streams.get(stream_id)

    def pending_count(self) -> int:
        return sum(1 for s in self._streams.values() if s == StreamStatus.PENDING)

    def result(self, stream_id: str) -> Optional[Any]:
        return self._results.get(stream_id)

    def completed_streams(self) -> List[str]:
        return [sid for sid, status in self._streams.items() if status == StreamStatus.COMPLETED]
