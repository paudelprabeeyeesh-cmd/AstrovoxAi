import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional


class LogEntry:
    def __init__(self, level: str, message: str, timestamp: Optional[float] = None, **kwargs: Any):
        self.level = level
        self.message = message
        self.timestamp = timestamp or time.time()
        self.timestamp_str = datetime.fromtimestamp(self.timestamp).isoformat()
        self.fields: Dict[str, Any] = dict(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp,
            "timestamp_str": self.timestamp_str,
            **self.fields,
        }


class LogAggregator:
    LEVEL_DEBUG = "debug"
    LEVEL_INFO = "info"
    LEVEL_WARNING = "warning"
    LEVEL_ERROR = "error"
    LEVEL_CRITICAL = "critical"

    def __init__(self):
        self._logs: List[LogEntry] = []
        self._counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self._level_counts: Dict[str, int] = defaultdict(int)

    def log(self, level: str, message: str, **kwargs: Any):
        entry = LogEntry(level=level, message=message, **kwargs)
        with self._lock:
            self._logs.append(entry)
            self._counts[message] += 1
            self._level_counts[level] += 1

    def debug(self, message: str, **kwargs: Any):
        self.log(self.LEVEL_DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any):
        self.log(self.LEVEL_INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any):
        self.log(self.LEVEL_WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any):
        self.log(self.LEVEL_ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any):
        self.log(self.LEVEL_CRITICAL, message, **kwargs)

    def filter_by_level(self, min_level: str) -> List[Dict[str, Any]]:
        levels = [self.LEVEL_DEBUG, self.LEVEL_INFO, self.LEVEL_WARNING, self.LEVEL_ERROR, self.LEVEL_CRITICAL]
        min_index = levels.index(min_level)
        with self._lock:
            return [entry.to_dict() for entry in self._logs if levels.index(entry.level) >= min_index]

    def filter_by_message(self, pattern: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [entry.to_dict() for entry in self._logs if pattern in entry.message]

    def get_most_common(self, n: int = 10) -> List[tuple]:
        with self._lock:
            return sorted(self._counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_level_counts(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._level_counts)

    def get_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [entry.to_dict() for entry in self._logs]

    def clear(self):
        with self._lock:
            self._logs.clear()
            self._counts.clear()
            self._level_counts.clear()
