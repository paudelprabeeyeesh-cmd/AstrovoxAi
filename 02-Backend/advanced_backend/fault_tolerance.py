import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _failures: int = field(default=0, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)
    _half_open_calls: int = field(default=0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise RuntimeError(f"Circuit breaker {self.name} is OPEN")
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise RuntimeError(f"Circuit breaker {self.name} is HALF_OPEN (throttled)")
                self._half_open_calls += 1
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise exc

    def _on_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED
            self._half_open_calls = 0

    def _on_failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._half_open_calls = 0

    def state(self) -> str:
        return self._state.value

    def metrics(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state(),
            "failures": self._failures,
            "last_failure": self._last_failure_time,
        }


class Bulkhead:
    def __init__(self, max_concurrent: int = 10) -> None:
        self._max = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active = 0
        self._lock = threading.Lock()

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        acquired = self._semaphore.acquire(timeout=5)
        if not acquired:
            raise RuntimeError("Bulkhead rejected call: pool exhausted")
        with self._lock:
            self._active += 1
        try:
            return func(*args, **kwargs)
        finally:
            with self._lock:
                self._active -= 1
            self._semaphore.release()

    def active(self) -> int:
        with self._lock:
            return self._active


class TimeoutPolicy:
    def __init__(self, seconds: float = 5.0) -> None:
        self.seconds = seconds

    def run(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(func, *args, **kwargs)
            return future.result(timeout=self.seconds)
