"""Fault tolerance for AI core."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    max_retries: int = 3
    backoff_factor: float = 2.0
    max_delay_seconds: float = 60.0


class AITFaultTolerance:
    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()

    def retry(self, func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, self.policy.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == self.policy.max_retries:
                        raise
            raise RuntimeError("unreachable")
        return wrapper


ai_fault_tolerance = AITFaultTolerance()
