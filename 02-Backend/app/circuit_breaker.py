"""Layer 9 — Circuit breakers, token quotas, cost monitoring.

Phase 350 — AI Reliability Foundation:
Unified error handling, retry engine, timeout management, request/response
validation, health monitoring, service degradation, maintenance mode, automatic
diagnostics, failure analytics, error categorization, crash recovery, graceful
shutdown, startup verification, configuration validation, production readiness.
"""

import time
import logging
import asyncio
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Phase 350 — Unified Error Handling & Exception Hierarchy
# ============================================================================

class AstrovoxError(Exception):
    """Base exception for all AstrovoxAI errors."""
    def __init__(self, message: str, code: str = "UNKNOWN", details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.timestamp = time.time()


class ProviderError(AstrovoxError):
    """AI provider error."""
    def __init__(self, message: str, provider: str = "", **kwargs):
        super().__init__(message, code="PROVIDER_ERROR", **kwargs)
        self.provider = provider


class ValidationError(AstrovoxError):
    """Input validation error."""
    def __init__(self, message: str, field: str = "", **kwargs):
        super().__init__(message, code="VALIDATION_ERROR", **kwargs)
        self.field = field


class QuotaExceededError(AstrovoxError):
    """Quota exceeded error."""
    def __init__(self, message: str, quota_type: str = "", **kwargs):
        super().__init__(message, code="QUOTA_EXCEEDED", **kwargs)
        self.quota_type = quota_type


class SecurityError(AstrovoxError):
    """Security violation error."""
    def __init__(self, message: str, threat_type: str = "", **kwargs):
        super().__init__(message, code="SECURITY_ERROR", **kwargs)
        self.threat_type = threat_type


class ErrorCategory(Enum):
    """Error categories for analytics."""
    PROVIDER = "provider"
    VALIDATION = "validation"
    QUOTA = "quota"
    SECURITY = "security"
    NETWORK = "network"
    TIMEOUT = "timeout"
    INTERNAL = "internal"


@dataclass
class ErrorEvent:
    """An error event for analytics."""
    error_type: str
    category: ErrorCategory
    message: str
    timestamp: float
    provider: str = ""
    user_id: str = ""
    resolved: bool = False


class ErrorAnalytics:
    """Track and analyze errors."""

    def __init__(self):
        self._errors: list[ErrorEvent] = []

    def record(self, error: AstrovoxError, category: ErrorCategory, **kwargs):
        """Record an error event."""
        event = ErrorEvent(
            error_type=type(error).__name__,
            category=category,
            message=str(error),
            timestamp=time.time(),
            **kwargs,
        )
        self._errors.append(event)

    def get_error_rate(self, window_seconds: int = 3600) -> float:
        """Get error rate in a time window."""
        cutoff = time.time() - window_seconds
        recent = [e for e in self._errors if e.timestamp >= cutoff]
        return len(recent) / max(window_seconds / 60, 1)

    def get_top_errors(self, limit: int = 10) -> list[dict]:
        """Get most common errors."""
        from collections import Counter
        counts = Counter(e.error_type for e in self._errors)
        return [{"error": k, "count": v} for k, v in counts.most_common(limit)]

    def get_by_category(self) -> dict:
        """Get error counts by category."""
        from collections import Counter
        return dict(Counter(e.category.value for e in self._errors))


# ============================================================================
# Phase 350 — Retry Engine
# ============================================================================

class RetryPolicy:
    """Configurable retry policy."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_backoff: bool = True,
        retryable_errors: tuple = (ProviderError, TimeoutError, ConnectionError),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.retryable_errors = retryable_errors

    def get_delay(self, attempt: int) -> float:
        """Get delay for a retry attempt."""
        if self.exponential_backoff:
            return min(self.base_delay * (2 ** attempt), self.max_delay)
        return self.base_delay


class RetryEngine:
    """Execute functions with retry logic."""

    def __init__(self, policy: RetryPolicy = None):
        self._policy = policy or RetryPolicy()

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with retries."""
        last_error = None

        for attempt in range(self._policy.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if attempt < self._policy.max_retries:
                    if isinstance(e, self._policy.retryable_errors):
                        delay = self._policy.get_delay(attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{self._policy.max_retries} "
                            f"after {delay:.1f}s: {str(e)[:100]}"
                        )
                        await asyncio.sleep(delay)
                        continue

                raise

        raise last_error


# ============================================================================
# Phase 350 — Timeout Management
# ============================================================================

class TimeoutManager:
    """Manage timeouts for different operation types."""

    def __init__(self):
        self._timeouts: dict[str, float] = {
            "default": 30.0,
            "chat": 60.0,
            "embedding": 30.0,
            "health": 5.0,
            "database": 10.0,
            "file_upload": 120.0,
        }

    def get_timeout(self, operation: str) -> float:
        """Get timeout for an operation."""
        return self._timeouts.get(operation, self._timeouts["default"])

    def set_timeout(self, operation: str, timeout: float):
        """Set timeout for an operation."""
        self._timeouts[operation] = timeout


# ============================================================================
# Phase 350 — Service Degradation & Maintenance Mode
# ============================================================================

class SystemMode(Enum):
    """System operating mode."""
    NORMAL = "normal"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    READONLY = "readonly"


class ServiceDegradation:
    """Manage service degradation and maintenance mode."""

    def __init__(self):
        self._mode = SystemMode.NORMAL
        self._disabled_features: set = set()
        self._degradation_hooks: list = []

    @property
    def mode(self) -> SystemMode:
        return self._mode

    def set_mode(self, mode: SystemMode):
        """Set system mode."""
        old_mode = self._mode
        self._mode = mode
        logger.info(f"System mode changed: {old_mode.value} -> {mode.value}")

        for hook in self._degradation_hooks:
            try:
                hook(old_mode, mode)
            except Exception:
                pass

    def disable_feature(self, feature: str):
        """Disable a specific feature."""
        self._disabled_features.add(feature)
        logger.info(f"Feature disabled: {feature}")

    def enable_feature(self, feature: str):
        """Re-enable a feature."""
        self._disabled_features.discard(feature)

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        if self._mode == SystemMode.MAINTENANCE:
            return False
        if self._mode == SystemMode.READONLY and feature not in ("read", "search"):
            return False
        return feature not in self._disabled_features

    def on_mode_change(self, hook: Callable):
        """Register a mode change hook."""
        self._degradation_hooks.append(hook)


# ============================================================================
# Phase 350 — Production Readiness & Diagnostics
# ============================================================================

@dataclass
class ReadinessCheck:
    """A production readiness check."""
    name: str
    passed: bool
    message: str
    severity: str = "info"


class ProductionReadiness:
    """Verify production readiness."""

    def __init__(self):
        self._checks: list[Callable] = []

    def add_check(self, name: str, check_func: Callable, severity: str = "info"):
        """Add a readiness check."""
        self._checks.append({
            "name": name,
            "func": check_func,
            "severity": severity,
        })

    async def run_checks(self) -> list[ReadinessCheck]:
        """Run all readiness checks."""
        results = []
        for check in self._checks:
            try:
                passed = await check["func"]() if asyncio.iscoroutinefunction(check["func"]) else check["func"]()
                results.append(ReadinessCheck(
                    name=check["name"],
                    passed=passed,
                    message="OK" if passed else "Failed",
                    severity=check["severity"] if passed else "error",
                ))
            except Exception as e:
                results.append(ReadinessCheck(
                    name=check["name"],
                    passed=False,
                    message=str(e)[:200],
                    severity="error",
                ))
        return results

    def is_ready(self, results: list[ReadinessCheck]) -> bool:
        """Check if all critical checks passed."""
        return all(r.passed for r in results if r.severity in ("error", "critical"))


# ============================================================================
# Phase 350 — Graceful Shutdown
# ============================================================================

class GracefulShutdown:
    """Manage graceful shutdown."""

    def __init__(self):
        self._handlers: list[Callable] = []
        self._is_shutting_down = False

    def register(self, handler: Callable, name: str = ""):
        """Register a shutdown handler."""
        self._handlers.append({"func": handler, "name": name})

    async def shutdown(self):
        """Execute graceful shutdown."""
        self._is_shutting_down = True
        logger.info("Initiating graceful shutdown...")

        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler["func"]):
                    await handler["func"]()
                else:
                    handler["func"]()
            except Exception as e:
                logger.error(f"Shutdown handler '{handler['name']}' failed: {e}")

        logger.info("Graceful shutdown complete")

    @property
    def is_shutting_down(self) -> bool:
        return self._is_shutting_down


# ============================================================================
# Singletons
# ============================================================================

error_analytics = ErrorAnalytics()
retry_engine = RetryEngine()
timeout_manager = TimeoutManager()
service_degradation = ServiceDegradation()
production_readiness = ProductionReadiness()
graceful_shutdown = GracefulShutdown()


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
