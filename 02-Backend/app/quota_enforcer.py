"""Usage quota enforcement for AI inference requests."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from .usage import DailyUsageTracker, UsageQuotaExceeded

logger = logging.getLogger(__name__)


@dataclass
class QuotaConfig:
    daily_limit: int = 100
    monthly_limit: int = 3000
    minute_limit: int = 20
    token_daily_limit: int = 500_000
    token_minute_limit: int = 50_000
    burst_limit: int = 10


@dataclass
class QuotaCheckResult:
    allowed: bool
    remaining_daily: int
    remaining_monthly: int
    remaining_minute: int
    remaining_token_daily: int
    reason: str = ""


class UsageQuotaEnforcer:
    def __init__(self, config: Optional[QuotaConfig] = None, tracker: Optional[DailyUsageTracker] = None):
        self.config = config or QuotaConfig()
        self.tracker = tracker or DailyUsageTracker(limit=self.config.daily_limit)
        self._minute_windows: dict[str, list[float]] = {}
        self._token_windows: dict[str, list[tuple[float, int]]] = {}

    def check(self, user_id: str, tokens: int = 0) -> QuotaCheckResult:
        daily = self.tracker.get_count(user_id)
        remaining_daily = max(0, self.config.daily_limit - daily)
        remaining_monthly = max(0, self.config.monthly_limit - daily * 30)
        remaining_minute = self._check_minute_window(user_id)
        remaining_token_daily = self._check_token_window(user_id, tokens)
        if remaining_daily <= 0:
            return QuotaCheckResult(
                allowed=False,
                remaining_daily=0,
                remaining_monthly=remaining_monthly,
                remaining_minute=remaining_minute,
                remaining_token_daily=remaining_token_daily,
                reason="Daily quota exceeded",
            )
        if remaining_minute <= 0:
            return QuotaCheckResult(
                allowed=False,
                remaining_daily=remaining_daily,
                remaining_monthly=remaining_monthly,
                remaining_minute=0,
                remaining_token_daily=remaining_token_daily,
                reason="Per-minute quota exceeded",
            )
        if remaining_token_daily <= 0:
            return QuotaCheckResult(
                allowed=False,
                remaining_daily=remaining_daily,
                remaining_monthly=remaining_monthly,
                remaining_minute=remaining_minute,
                remaining_token_daily=0,
                reason="Daily token quota exceeded",
            )
        return QuotaCheckResult(
            allowed=True,
            remaining_daily=remaining_daily,
            remaining_monthly=remaining_monthly,
            remaining_minute=remaining_minute,
            remaining_token_daily=remaining_token_daily,
            reason="OK",
        )

    def record(self, user_id: str, tokens: int = 0) -> None:
        try:
            self.tracker.record_success(user_id)
        except UsageQuotaExceeded:
            raise
        self._record_minute_window(user_id)
        self._record_token_window(user_id, tokens)

    def _check_minute_window(self, user_id: str) -> int:
        now = time.time()
        window = self._minute_windows.get(user_id, [])
        window = [t for t in window if now - t < 60]
        self._minute_windows[user_id] = window
        return max(0, self.config.minute_limit - len(window))

    def _check_token_window(self, user_id: str, tokens: int) -> int:
        now = time.time()
        window = self._token_windows.get(user_id, [])
        window = [(t, tok) for t, tok in window if now - t < 86400]
        used = sum(tok for _, tok in window)
        self._token_windows[user_id] = window
        return max(0, self.config.token_daily_limit - used - tokens)

    def _record_minute_window(self, user_id: str) -> None:
        now = time.time()
        self._minute_windows.setdefault(user_id, []).append(now)
        self._minute_windows[user_id] = [t for t in self._minute_windows[user_id] if now - t < 60]

    def _record_token_window(self, user_id: str, tokens: int) -> None:
        now = time.time()
        self._token_windows.setdefault(user_id, []).append((now, tokens))
        self._token_windows[user_id] = [(t, tok) for t, tok in self._token_windows[user_id] if now - t < 86400]
