"""Transaction retry helper for transient database errors."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, TypeVar

from sqlalchemy.exc import OperationalError, IntegrityError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TransactionRetry:
    """Retry database transactions on transient errors."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 2.0,
        retryable_exceptions: tuple[type[Exception], ...] = (OperationalError, IntegrityError),
    ) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._retryable_exceptions = retryable_exceptions

    def run(self, fn: Callable[[], T]) -> T:
        last_exc = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return fn()
            except self._retryable_exceptions as exc:
                last_exc = exc
                delay = min(self._base_delay * (2 ** (attempt - 1)), self._max_delay)
                logger.warning("Transaction failed (attempt %d/%d): %s. Retrying in %.2fs", attempt, self._max_retries, exc, delay)
                time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    def __call__(self, fn: Callable[[], T]) -> Callable[[], T]:
        def wrapper() -> T:
            return self.run(fn)
        return wrapper
