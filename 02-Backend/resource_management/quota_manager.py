import threading
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Quota:
    cpu_seconds: float = 0.0
    memory_bytes: int = 0
    io_bytes: int = 0
    requests: int = 0


class QuotaManager:
    def __init__(self) -> None:
        self._quotas: Dict[str, Quota] = {}
        self._limits: Dict[str, Quota] = {}
        self._lock = threading.Lock()

    def set_limit(self, subject: str, limit: Quota) -> None:
        with self._lock:
            self._limits[subject] = limit

    def consume(self, subject: str, usage: Quota) -> bool:
        with self._lock:
            current = self._quotas.get(subject, Quota())
            limit = self._limits.get(subject)
            if limit:
                if current.cpu_seconds + usage.cpu_seconds > limit.cpu_seconds:
                    return False
                if current.memory_bytes + usage.memory_bytes > limit.memory_bytes:
                    return False
                if current.requests + usage.requests > limit.requests:
                    return False
            current.cpu_seconds += usage.cpu_seconds
            current.memory_bytes += usage.memory_bytes
            current.io_bytes += usage.io_bytes
            current.requests += usage.requests
            self._quotas[subject] = current
            return True

    def reset(self, subject: str) -> None:
        with self._lock:
            self._quotas.pop(subject, None)

    def report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                s: {
                    "cpu_seconds": q.cpu_seconds,
                    "memory_bytes": q.memory_bytes,
                    "io_bytes": q.io_bytes,
                    "requests": q.requests,
                }
                for s, q in self._quotas.items()
            }
