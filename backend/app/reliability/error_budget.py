"""Error budget policy enforcement."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class ErrorBudgetPolicy:
    slo_target: float = 0.999
    window_days: int = 30
    fast_burn_threshold: float = 14.4
    slow_burn_threshold: float = 3.0
    max_violations_before_freeze: int = 3


class ErrorBudgetEnforcer:
    def __init__(self, policy: Optional[ErrorBudgetPolicy] = None) -> None:
        self.policy = policy or ErrorBudgetPolicy()
        self._total_requests: int = 0
        self._errors: int = 0
        self._window_start = datetime.now(timezone.utc)
        self._violations: int = 0

    def record_request(self, is_error: bool = False) -> None:
        self._total_requests += 1
        if is_error:
            self._errors += 1

    def error_rate(self) -> float:
        if self._total_requests == 0:
            return 0.0
        return self._errors / self._total_requests

    def remaining(self) -> float:
        allowed = self._total_requests * (1.0 - self.policy.slo_target)
        if allowed <= 0:
            return 1.0
        return max(0.0, (allowed - self._errors) / allowed)

    def burn_rate(self) -> float:
        allowed = 1.0 - self.policy.slo_target
        if allowed <= 0:
            return 0.0
        return self.error_rate() / allowed

    def should_freeze_deploys(self) -> bool:
        if self.remaining() <= 0.0 and self._violations >= self.policy.max_violations_before_freeze:
            return True
        return False

    def snapshot(self) -> Dict[str, Optional[str]]:
        return {
            "total_requests": str(self._total_requests),
            "errors": str(self._errors),
            "error_rate": str(round(self.error_rate(), 6)),
            "burn_rate": str(round(self.burn_rate(), 4)),
            "remaining": str(round(self.remaining(), 4)),
            "window_start": self._window_start.isoformat(),
        }
