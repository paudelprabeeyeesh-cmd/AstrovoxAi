"""Retry policies with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Callable, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Configurable retry policy with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,),
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay = random.uniform(0, delay)
        return delay

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except self.retryable_exceptions as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    logger.warning(f"Retry {attempt + 1}/{self.max_retries} after {delay:.2f}s: {exc}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Max retries exceeded: {exc}")
                    raise
        raise last_exception  # type: ignore


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator for adding retry logic to functions."""
    def decorator(func: Callable) -> Callable:
        policy = RetryPolicy(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await policy.execute(func, *args, **kwargs)

        return wrapper
    return decorator


class RetryBudget:
    """Track retry budget to prevent retry storms."""

    def __init__(self, max_retries_per_minute: int = 100) -> None:
        self.max_retries_per_minute = max_retries_per_minute
        self._retries: list = []

    def can_retry(self) -> bool:
        now = time.time()
        self._retries = [t for t in self._retries if now - t < 60]
        return len(self._retries) < self.max_retries_per_minute

    def record_retry(self) -> None:
        self._retries.append(time.time())

    def get_remaining(self) -> int:
        now = time.time()
        self._retries = [t for t in self._retries if now - t < 60]
        return self.max_retries_per_minute - len(self._retries)


_retry_budget: Optional[RetryBudget] = None


def get_retry_budget() -> RetryBudget:
    global _retry_budget
    if _retry_budget is None:
        _retry_budget = RetryBudget()
    return _retry_budget
