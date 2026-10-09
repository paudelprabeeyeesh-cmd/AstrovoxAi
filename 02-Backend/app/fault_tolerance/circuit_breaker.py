import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str = "default"
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    success_threshold: int = 1
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _failures: int = field(default=0, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)
    _half_open_calls: int = field(default=0, init=False, repr=False)
    _success_count: int = field(default=0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
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
        except Exception as exc:  # noqa: BLE001
            self._on_failure()
            raise exc

    def _on_success(self) -> None:
        with self._lock:
            self._failures = 0
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._half_open_calls = 0
                    self._success_count = 0
                    logger.info("Circuit breaker %s closed after successful recovery", self.name)
            else:
                self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
                self._success_count = 0

    def _maybe_recover(self) -> None:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0

    def state(self) -> str:
        with self._lock:
            self._maybe_recover()
            return self._state.value

    def get_state(self) -> str:
        return self.state()

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._success_count = 0
            self._state = CircuitState.CLOSED
            self._last_failure_time = 0.0
            self._half_open_calls = 0

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state(),
                "failures": self._failures,
                "last_failure": self._last_failure_time,
            }
