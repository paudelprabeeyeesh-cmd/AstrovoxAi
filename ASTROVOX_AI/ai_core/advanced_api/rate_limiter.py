"""AI rate limiter."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing: Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIRateLimitRule:
    key: str
    limit: int
    window_seconds: float


class AIAdvancedRateLimiter:
    def __init__(self) -> None:
        self._windows: Dict[str, List[float]] = {}
        self._rules: Dict[str, AIRateLimitRule] = {}

    def add_rule(self, rule: AIRateLimitRule) -> None:
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


ai_advanced_rate_limiter = AIAdvancedRateLimiter()
