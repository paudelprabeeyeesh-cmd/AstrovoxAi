"""Error budget tracking."""
from datetime import datetime, timezone
from typing import Dict, Optional


class ErrorBudgetTracker:
    def __init__(self, total_requests: int = 0, errors: int = 0):
        self._total_requests = total_requests
        self._errors = errors
        self._last_updated = datetime.now(timezone.utc)
        self._burn_rate_alerts: Dict[str, bool] = {}

    def record_request(self, is_error: bool = False):
        self._total_requests += 1
        if is_error:
            self._errors += 1
        self._last_updated = datetime.now(timezone.utc)

    def error_rate(self) -> float:
        if self._total_requests == 0:
            return 0.0
        return self._errors / self._total_requests

    def error_budget_remaining(self, slo_target: float = 0.999) -> float:
        allowed_errors = self._total_requests * (1.0 - slo_target)
        if allowed_errors <= 0:
            return 1.0
        remaining = allowed_errors - self._errors
        return max(0.0, remaining / allowed_errors)

    def burn_rate(self, slo_target: float = 0.999) -> float:
        if self._total_requests == 0:
            return 0.0
        actual = self.error_rate()
        allowed = 1.0 - slo_target
        if allowed <= 0:
            return 0.0
        return actual / allowed

    def should_page(self, slo_target: float = 0.999, fast_burn_threshold: float = 14.4) -> bool:
        return self.burn_rate(slo_target) >= fast_burn_threshold

    def should_warn(self, slo_target: float = 0.999, slow_burn_threshold: float = 3.0) -> bool:
        return self.burn_rate(slo_target) >= slow_burn_threshold

    def snapshot(self) -> Dict[str, Optional[str]]:
        return {
            "total_requests": str(self._total_requests),
            "errors": str(self._errors),
            "error_rate": str(round(self.error_rate(), 6)),
            "burn_rate": str(round(self.burn_rate(), 4)),
            "last_updated": self._last_updated.isoformat(),
        }
