"""Advanced rate limiting."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    key: str
    limit: int
    window_seconds: float


class AdvancedRateLimiter:
    def __init__(self) -> None:
        self._windows: Dict[str, List[float]] = {}
        self._rules: Dict[str, RateLimitRule] = {}

    def add_rule(self, rule: RateLimitRule) -> None:
        self._rules[rule.key] = rule

    def is_allowed(self, key: str) -> bool:
        rule = self._rules.get(key)
        if not rule:
            return True
        now = time.time()
        window = self._windows.setdefault(key, [])
        window[:] = [t for t in window if now - t < rule.window_seconds]
        if len(window) >= rule.limit:
            return False
        window.append(now)
        return True


advanced_rate_limiter = AdvancedRateLimiter()
