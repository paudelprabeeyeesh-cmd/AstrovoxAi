import asyncio
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitMetrics:
    name: str
    state: str = "closed"
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    opened_at: Optional[float] = None
    total_calls: int = 0
    rejected_calls: int = 0


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 1,
        half_open_max_calls: int = 3,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.half_open_max_calls = half_open_max_calls
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._total_calls = 0
        self._rejected_calls = 0
        self._half_open_calls = 0

    def _maybe_recover(self) -> None:
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            if time.time() - self._opened_at >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker %s transitioned to half-open", self.name)

    def get_state(self) -> str:
        with self._lock:
            self._maybe_recover()
            return self._state.value

    def metrics(self) -> CircuitMetrics:
        with self._lock:
            self._maybe_recover()
            return CircuitMetrics(
                name=self.name,
                state=self._state.value,
                failure_count=self._failure_count,
                success_count=self._success_count,
                last_failure_time=self._last_failure_time,
                last_success_time=self._last_success_time,
                opened_at=self._opened_at,
                total_calls=self._total_calls,
                rejected_calls=self._rejected_calls,
            )

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            self._maybe_recover()
            if self._state == CircuitState.OPEN:
                self._rejected_calls += 1
                raise RuntimeError(f"Circuit breaker {self.name} is open")
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    self._rejected_calls += 1
                    raise RuntimeError(f"Circuit breaker {self.name} is half-open (throttled)")
                self._half_open_calls += 1
            self._total_calls += 1
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise exc

    async def call_async(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            self._maybe_recover()
            if self._state == CircuitState.OPEN:
                self._rejected_calls += 1
                raise RuntimeError(f"Circuit breaker {self.name} is open")
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    self._rejected_calls += 1
                    raise RuntimeError(f"Circuit breaker {self.name} is half-open (throttled)")
                self._half_open_calls += 1
            self._total_calls += 1
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise exc

    def _on_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._last_success_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._success_count = 0
                    self._half_open_calls = 0
                    logger.info("Circuit breaker %s closed after recovery", self.name)
            else:
                self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
                self._half_open_calls = 0
                logger.error("Circuit breaker %s opened due to failures", self.name)

    def reset(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._success_count = 0
            self._state = CircuitState.CLOSED
            self._last_failure_time = None
            self._last_success_time = None
            self._opened_at = None
            self._total_calls = 0
            self._rejected_calls = 0
            self._half_open_calls = 0


llm_circuit_breaker = CircuitBreaker(
    name="llm", failure_threshold=5, recovery_timeout=60, success_threshold=1
)
db_circuit_breaker = CircuitBreaker(
    name="database", failure_threshold=3, recovery_timeout=30, success_threshold=1
)
redis_circuit_breaker = CircuitBreaker(
    name="redis", failure_threshold=3, recovery_timeout=30, success_threshold=1
)
external_api_circuit_breaker = CircuitBreaker(
    name="external_api", failure_threshold=10, recovery_timeout=120, success_threshold=1
)
