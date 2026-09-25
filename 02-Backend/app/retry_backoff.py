"""Retry with exponential backoff."""

from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import time


@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True


class RetryWithBackoff:
    @staticmethod
    async def execute(func: Callable, config: RetryConfig, *args, **kwargs) -> Any:
        attempt = 0
        delay = config.initial_delay
        last_exception = None
        while attempt < config.max_attempts:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                attempt += 1
                if attempt >= config.max_attempts:
                    break
                actual_delay = delay
                if config.jitter:
                    actual_delay = delay * (0.5 + 0.5 * hash(time.time()) % 100 / 100)
                await asyncio.sleep(min(actual_delay, config.max_delay))
                delay = min(delay * config.backoff_factor, config.max_delay)
        raise last_exception

    @staticmethod
    def execute_sync(func: Callable, config: RetryConfig, *args, **kwargs) -> Any:
        attempt = 0
        delay = config.initial_delay
        last_exception = None
        while attempt < config.max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                attempt += 1
                if attempt >= config.max_attempts:
                    break
                actual_delay = delay
                if config.jitter:
                    actual_delay = delay * (0.5 + 0.5 * hash(time.time()) % 100 / 100)
                time.sleep(min(actual_delay, config.max_delay))
                delay = min(delay * config.backoff_factor, config.max_delay)
        raise last_exception
