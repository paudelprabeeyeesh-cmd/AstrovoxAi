import logging
import time
from enum import Enum
from typing import Callable, Tuple, Type, Any

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


class RetryPolicy:
    def __init__(self, max_retries: int = 3, backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL, base_delay: float = 1.0, max_delay: float = 60.0, retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)):
        self.max_retries = max_retries
        self.backoff_strategy = backoff_strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retryable_exceptions = retryable_exceptions

    def _get_delay(self, attempt: int) -> float:
        if self.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            return min(self.base_delay * (2 ** attempt), self.max_delay)
        return self.base_delay

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.retryable_exceptions as exc:
                last_exception = exc
                logger.warning("Attempt %d failed: %s", attempt + 1, exc)
                if attempt < self.max_retries:
                    delay = self._get_delay(attempt)
                    time.sleep(delay)
                else:
                    raise last_exception
        raise last_exception

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        return attempt < self.max_retries and isinstance(exception, self.retryable_exceptions)
