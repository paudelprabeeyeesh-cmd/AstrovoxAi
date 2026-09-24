import sys
import threading
from dataclasses import dataclass
from typing import Any, Optional


class ResourceLimiter:
    def __init__(self, max_memory_mb: int = 256, max_execution_time: float = 1.0):
        self.max_memory_mb = max_memory_mb
        self.max_execution_time = max_execution_time
        self._timer: Optional[threading.Timer] = None

    def limit_memory(self, limit_mb: Optional[int] = None) -> None:
        mem_limit = limit_mb if limit_mb is not None else self.max_memory_mb
        bytes_limit = mem_limit * 1024 * 1024
        if sys.platform != "win32":
            try:
                import resource
                resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
            except (ValueError, ImportError, OSError):
                pass

    def limit_cpu_time(self) -> None:
        if sys.platform != "win32":
            try:
                import resource
                soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
                resource.setrlimit(
                    resource.RLIMIT_CPU,
                    (max(soft, 1), max(hard, 1)),
                )
            except (ValueError, ImportError, OSError):
                pass

    def enforce(self) -> None:
        self.limit_memory()
        self.limit_cpu_time()

    def enforce_with_timeout(self) -> None:
        self._cancel_timer()
        self.enforce()
        if sys.platform != "win32":
            import signal
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(max(1, int(self.max_execution_time)))
        else:
            self._timer = threading.Timer(
                self.max_execution_time, self._timeout_handler
            )
            self._timer.daemon = True
            self._timer.start()

    def _timeout_handler(self, signum: int = 0, frame: Any = None) -> None:
        self._cancel_timer()
        raise TimeoutError(f"execution exceeded {self.max_execution_time}s")

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
