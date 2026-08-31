"""Layer 9 — Circuit breakers, token quotas, and cost monitoring."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker state."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for AI providers."""
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    half_open_calls: int = 0

    def can_execute(self) -> bool:
        """Check if a call can be made."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def record_success(self):
        """Record a successful call."""
        self.success_count += 1
        self.last_success_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' opened after {self.failure_count} failures")


class CircuitBreakerManager:
    """Manage circuit breakers for all providers."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name)
        return self._breakers[name]

    def get_all_breakers(self) -> dict[str, CircuitBreaker]:
        """Get all circuit breakers."""
        return dict(self._breakers)

    def get_status(self) -> dict:
        """Get status of all breakers."""
        return {
            name: {
                "state": breaker.state.value,
                "failures": breaker.failure_count,
                "successes": breaker.success_count,
            }
            for name, breaker in self._breakers.items()
        }


@dataclass
class TokenQuota:
    """Token quota for a user."""
    user_id: str
    daily_token_limit: int = 100000
    monthly_token_limit: int = 2000000
    daily_used: int = 0
    monthly_used: int = 0
    last_reset_daily: float = 0.0
    last_reset_monthly: float = 0.0

    def check_quota(self, requested_tokens: int = 1000) -> tuple[bool, str]:
        """Check if a request is within quota."""
        now = time.time()

        if now - self.last_reset_daily >= 86400:
            self.daily_used = 0
            self.last_reset_daily = now

        if now - self.last_reset_monthly >= 2592000:
            self.monthly_used = 0
            self.last_reset_monthly = now

        if self.daily_used + requested_tokens > self.daily_token_limit:
            remaining = self.daily_token_limit - self.daily_used
            return False, f"Daily token quota exceeded. Remaining: {remaining}"

        if self.monthly_used + requested_tokens > self.monthly_token_limit:
            remaining = self.monthly_token_limit - self.monthly_used
            return False, f"Monthly token quota exceeded. Remaining: {remaining}"

        return True, ""

    def record_usage(self, tokens: int):
        """Record token usage."""
        self.daily_used += tokens
        self.monthly_used += tokens

    def get_remaining(self) -> dict:
        """Get remaining quota."""
        return {
            "daily_remaining": max(0, self.daily_token_limit - self.daily_used),
            "monthly_remaining": max(0, self.monthly_token_limit - self.monthly_used),
            "daily_used": self.daily_used,
            "monthly_used": self.monthly_used,
        }


class QuotaManager:
    """Manage token quotas for all users."""

    def __init__(self):
        self._quotas: dict[str, TokenQuota] = {}

    def get_quota(self, user_id: str) -> TokenQuota:
        """Get or create a quota."""
        if user_id not in self._quotas:
            self._quotas[user_id] = TokenQuota(user_id=user_id)
        return self._quotas[user_id]

    def check_quota(self, user_id: str, requested_tokens: int = 1000) -> tuple[bool, str]:
        """Check if a user has quota remaining."""
        quota = self.get_quota(user_id)
        return quota.check_quota(requested_tokens)

    def record_usage(self, user_id: str, tokens: int):
        """Record token usage."""
        quota = self.get_quota(user_id)
        quota.record_usage(tokens)

    def get_all_quotas(self) -> dict:
        """Get all quotas."""
        return {
            user_id: quota.get_remaining()
            for user_id, quota in self._quotas.items()
        }


class CostMonitor:
    """Monitor and alert on costs."""

    def __init__(self):
        self._daily_costs: dict[str, float] = {}
        self._monthly_costs: dict[str, float] = {}
        self._alerts: list[dict] = []

    def record_cost(self, user_id: str, cost: float):
        """Record a cost."""
        today = time.time() // 86400
        month = time.time() // 2592000

        self._daily_costs[f"{user_id}:{today}"] = self._daily_costs.get(f"{user_id}:{today}", 0) + cost
        self._monthly_costs[f"{user_id}:{month}"] = self._monthly_costs.get(f"{user_id}:{month}", 0) + cost

        daily = self._daily_costs[f"{user_id}:{today}"]
        monthly = self._monthly_costs[f"{user_id}:{month}"]

        if daily > 10.0:
            self._alerts.append({
                "type": "daily_cost_exceeded",
                "user_id": user_id,
                "amount": daily,
                "timestamp": time.time(),
            })

        if monthly > 100.0:
            self._alerts.append({
                "type": "monthly_cost_exceeded",
                "user_id": user_id,
                "amount": monthly,
                "timestamp": time.time(),
            })

    def get_daily_cost(self, user_id: str) -> float:
        """Get today's cost."""
        today = time.time() // 86400
        return self._daily_costs.get(f"{user_id}:{today}", 0)

    def get_monthly_cost(self, user_id: str) -> float:
        """Get this month's cost."""
        month = time.time() // 2592000
        return self._monthly_costs.get(f"{user_id}:{month}", 0)

    def get_alerts(self) -> list[dict]:
        """Get cost alerts."""
        return list(self._alerts)


circuit_breaker_manager = CircuitBreakerManager()
quota_manager = QuotaManager()
cost_monitor = CostMonitor()
