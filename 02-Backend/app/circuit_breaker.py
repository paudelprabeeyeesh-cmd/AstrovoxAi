import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    f"Circuit breaker {self.name} transitioned to half-open"
                )
            else:
                raise Exception(f"Circuit breaker {self.name} is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info(
                    f"Circuit breaker {self.name} closed after successful recovery"
                )
        else:
            self.state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self._opened_at = time.time()
            logger.error(
                f"Circuit breaker {self.name} opened due to failures"
            )

    def _should_attempt_reset(self) -> bool:
        if self._opened_at is None:
            return False
        return time.time() - self._opened_at >= self.recovery_timeout

    def get_state(self) -> str:
        return self.state.value

    def reset(self) -> None:
        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
        self._opened_at = None


llm_circuit_breaker = CircuitBreaker(
    name="llm", failure_threshold=5, recovery_timeout=60, success_threshold=3
)
db_circuit_breaker = CircuitBreaker(
    name="database", failure_threshold=3, recovery_timeout=30, success_threshold=2
)
redis_circuit_breaker = CircuitBreaker(
    name="redis", failure_threshold=3, recovery_timeout=30, success_threshold=2
)
external_api_circuit_breaker = CircuitBreaker(
    name="external_api", failure_threshold=10, recovery_timeout=120, success_threshold=5
)
