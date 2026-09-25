"""Retry budget and concurrency limiter."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryBudget:
    """Budget for retry attempts across the system."""

    max_retries: int = 100
    window_seconds: float = 60.0
    _used: int = field(default=0, repr=False)
    _window_start: float = field(default_factory=time.time, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def acquire(self, retries: int = 1) -> bool:
        """Try to acquire retry budget. Returns True if allowed."""
        with self._lock:
            now = time.time()
            if now - self._window_start >= self._window_seconds:
                self._used = 0
                self._window_start = now
            if self._used + retries > self.max_retries:
                return False
            self._used += retries
            return True

    def release(self, retries: int = 1) -> None:
        """Release unused retry budget."""
        with self._lock:
            self._used = max(0, self._used - retries)

    def remaining(self) -> int:
        """Get remaining retry budget in current window."""
        with self._lock:
            now = time.time()
            if now - self._window_start >= self._window_seconds:
                return self.max_retries
            return max(0, self.max_retries - self._used)

    def reset(self) -> None:
        """Reset the budget."""
        with self._lock:
            self._used = 0
            self._window_start = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """Get budget statistics."""
        with self._lock:
            now = time.time()
            return {
                "max_retries": self.max_retries,
                "used": self._used,
                "remaining": self.remaining(),
                "window_seconds": self._window_seconds,
                "window_start": self._window_start,
            }


class RetryBudgetManager:
    """Manage retry budgets for multiple services."""

    def __init__(self) -> None:
        self._budgets: Dict[str, RetryBudget] = {}
        self._lock = threading.Lock()

    def get_budget(self, name: str, max_retries: int = 100, window_seconds: float = 60.0) -> RetryBudget:
        """Get or create a retry budget."""
        with self._lock:
            if name not in self._budgets:
                self._budgets[name] = RetryBudget(
                    max_retries=max_retries,
                    window_seconds=window_seconds,
                )
            return self._budgets[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all budgets."""
        with self._lock:
            return {name: budget.get_stats() for name, budget in self._budgets.items()}


retry_budget_manager = RetryBudgetManager()


def with_retry_budget(budget_name: str, retries: int = 1):
    """Decorator to enforce retry budget before executing a function."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            budget = retry_budget_manager.get_budget(budget_name)
            if not budget.acquire(retries):
                raise RuntimeError(f"Retry budget exhausted for {budget_name}")
            try:
                return func(*args, **kwargs)
            finally:
                budget.release(retries)
        return wrapper
    return decorator


async def with_retry_budget_async(budget_name: str, retries: int = 1):
    """Async decorator to enforce retry budget."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            budget = retry_budget_manager.get_budget(budget_name)
            if not budget.acquire(retries):
                raise RuntimeError(f"Retry budget exhausted for {budget_name}")
            try:
                return await func(*args, **kwargs)
            finally:
                budget.release(retries)
        return wrapper
    return decorator
