import resource
import signal
import time
from dataclasses import dataclass
from typing import Optional


class ResourceLimiter:
    def __init__(self, max_memory_mb: int = 256, max_execution_time: float = 1.0):
        self.max_memory_mb = max_memory_mb
        self.max_execution_time = max_execution_time

    def limit_memory(self, limit_mb: Optional[int] = None) -> None:
        mem_limit = limit_mb if limit_mb is not None else self.max_memory_mb
        bytes_limit = mem_limit * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
        except (ValueError, resource.error):
            pass

    def limit_cpu_time(self) -> None:
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (max(soft, 1), max(hard, 1)),
            )
        except (ValueError, resource.error):
            pass

    def enforce(self) -> None:
        self.limit_memory()
        self.limit_cpu_time()

    def enforce_with_timeout(self) -> None:
        self.enforce()
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(max(1, int(self.max_execution_time)))

    def _timeout_handler(self, signum: int, frame: Any) -> None:
        raise TimeoutError(f"execution exceeded {self.max_execution_time}s")
