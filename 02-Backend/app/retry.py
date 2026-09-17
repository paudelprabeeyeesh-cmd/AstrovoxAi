import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)


class RetryBudgetExceeded(Exception):
    pass


class RetryBudget:
    def __init__(self, max_retries: int = 100, window_seconds: int = 60) -> None:
        self.max_retries = max_retries
        self.window_seconds = window_seconds
        self._retries: list[float] = []

    def record_retry(self) -> None:
        now = time.time()
        self._retries = [
            t for t in self._retries if now - t < self.window_seconds
        ]
        if len(self._retries) >= self.max_retries:
            raise RetryBudgetExceeded(
                f"Retry budget exceeded: {self.max_retries} retries in {self.window_seconds}s window"
            )
        self._retries.append(now)

    def remaining(self) -> int:
        now = time.time()
        self._retries = [
            t for t in self._retries if now - t < self.window_seconds
        ]
        return self.max_retries - len(self._retries)


_default_budget = RetryBudget()


def _calculate_delay(
    attempt: int, base_delay: float, max_delay: float, jitter: bool
) -> float:
    delay = min(base_delay * (2 ** attempt), max_delay)
    if jitter:
        delay = delay * (0.5 + random.random())
    return delay


def _retry_execute(
    func: Callable,
    args: Tuple[Any, ...],
    kwargs: dict[str, Any],
    max_retries: int,
    base_delay: float,
    max_delay: float,
    jitter: bool,
    retryable_exceptions: Tuple[Type[Exception], ...],
    budget: RetryBudget,
) -> Any:
    last_exception: Optional[BaseException] = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries:
                try:
                    budget.record_retry()
                except RetryBudgetExceeded:
                    logger.error("Retry budget exceeded, failing fast")
                    raise
                delay = _calculate_delay(attempt, base_delay, max_delay, jitter)
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} for {getattr(func, '__name__', repr(func))} after {delay:.2f}s: {e}"
                )
                time.sleep(delay)
    if last_exception is not None:
        raise last_exception
    raise RuntimeError("Retry failed without exception")


async def _retry_execute_async(
    func: Callable,
    args: Tuple[Any, ...],
    kwargs: dict[str, Any],
    max_retries: int,
    base_delay: float,
    max_delay: float,
    jitter: bool,
    retryable_exceptions: Tuple[Type[Exception], ...],
    budget: RetryBudget,
) -> Any:
    last_exception: Optional[BaseException] = None
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries:
                try:
                    budget.record_retry()
                except RetryBudgetExceeded:
                    logger.error("Retry budget exceeded, failing fast")
                    raise
                delay = _calculate_delay(attempt, base_delay, max_delay, jitter)
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} for {getattr(func, '__name__', repr(func))} after {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)
    if last_exception is not None:
        raise last_exception
    raise RuntimeError("Retry failed without exception")


def retry_with_backoff(
    func: Optional[Callable] = None,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    budget: Optional[RetryBudget] = None,
) -> Any:
    target_budget = budget if budget is not None else _default_budget

    if func is None:

        def decorator(fn: Callable) -> Callable:
            @wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return _retry_execute(
                    fn,
                    args,
                    kwargs,
                    max_retries,
                    base_delay,
                    max_delay,
                    jitter,
                    retryable_exceptions,
                    target_budget,
                )

            return wrapper

        return decorator
    else:

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return _retry_execute(
                func,
                args,
                kwargs,
                max_retries,
                base_delay,
                max_delay,
                jitter,
                retryable_exceptions,
                target_budget,
            )

        return wrapper


def retry_with_backoff_async(
    func: Optional[Callable] = None,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    budget: Optional[RetryBudget] = None,
) -> Any:
    target_budget = budget if budget is not None else _default_budget

    if func is None:

        def decorator(fn: Callable) -> Callable:
            @wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                return await _retry_execute_async(
                    fn,
                    args,
                    kwargs,
                    max_retries,
                    base_delay,
                    max_delay,
                    jitter,
                    retryable_exceptions,
                    target_budget,
                )

            return wrapper

        return decorator
    else:

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _retry_execute_async(
                func,
                args,
                kwargs,
                max_retries,
                base_delay,
                max_delay,
                jitter,
                retryable_exceptions,
                target_budget,
            )

        return wrapper
