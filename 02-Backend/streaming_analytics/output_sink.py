import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class OutputRecord:
    key: str
    value: Any
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class OutputSink:
    def __init__(self, max_buffer_size: int = 1000):
        self._buffer: List[OutputRecord] = []
        self._max_buffer_size = max_buffer_size
        self._lock = threading.Lock()
        self._flush_callbacks: List[Callable[[List[OutputRecord]], None]] = []

    def write(self, key: str, value: Any, timestamp: float, **metadata) -> bool:
        record = OutputRecord(
            key=key, value=value, timestamp=timestamp, metadata=metadata
        )
        with self._lock:
            if len(self._buffer) >= self._max_buffer_size:
                return False
            self._buffer.append(record)
            return True

    def write_batch(self, records: List[Dict[str, Any]]) -> int:
        written = 0
        for record in records:
            if self.write(
                record["key"],
                record["value"],
                record["timestamp"],
                **record.get("metadata", {}),
            ):
                written += 1
        return written

    def flush(self) -> List[OutputRecord]:
        with self._lock:
            records = list(self._buffer)
            self._buffer.clear()
        for callback in self._flush_callbacks:
            callback(records)
        return records

    def on_flush(self, callback: Callable[[List[OutputRecord]], None]) -> None:
        self._flush_callbacks.append(callback)

    def buffer_size(self) -> int:
        with self._lock:
            return len(self._buffer)

    def drain(self) -> List[OutputRecord]:
        return self.flush()

    def peek(self, n: Optional[int] = None) -> List[OutputRecord]:
        with self._lock:
            if n is None:
                return list(self._buffer)
            return list(self._buffer[:n])
