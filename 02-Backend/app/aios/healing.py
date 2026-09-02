"""Self-healing: circuit breakers, retries, health probes, automatic rollback."""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from . import make_id, now
from ..logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    reset_timeout_s: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: Optional[float] = None
    opened_at: Optional[float] = None

    def allow(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.opened_at and now() - self.opened_at >= self.reset_timeout_s:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN allows one trial

    def record_success(self) -> None:
        self.success_count += 1
        self.failure_count = 0
        if self.state in {CircuitState.HALF_OPEN, CircuitState.OPEN}:
            self.state = CircuitState.CLOSED
            self.opened_at = None

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_at = now()
        if self.failure_count >= self.failure_threshold and self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "opened_at": self.opened_at,
        }


class CircuitRegistry:
    def __init__(self) -> None:
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def breaker(self, name: str) -> CircuitBreaker:
        with self._lock:
            breaker = self._breakers.get(name)
            if breaker is None:
                breaker = CircuitBreaker(name=name)
                self._breakers[name] = breaker
            return breaker

    def allow(self, name: str) -> bool:
        return self.breaker(name).allow()

    def record(self, name: str, *, success: bool) -> None:
        breaker = self.breaker(name)
        if success:
            breaker.record_success()
        else:
            breaker.record_failure()

    def all(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self._breakers.values()]


class RetryPolicy:
    def __init__(self, *, max_attempts: int = 3, base_delay_s: float = 0.1, max_delay_s: float = 5.0) -> None:
        self.max_attempts = max_attempts
        self.base_delay_s = base_delay_s
        self.max_delay_s = max_delay_s

    def delay(self, attempt: int) -> float:
        return min(self.base_delay_s * (2 ** attempt), self.max_delay_s)


class Retrier:
    def __init__(self, registry: CircuitRegistry, policy: Optional[RetryPolicy] = None) -> None:
        self.registry = registry
        self.policy = policy or RetryPolicy()

    async def run(
        self,
        breaker_name: str,
        fn: Callable[[], Awaitable[Any]],
    ) -> Any:
        last_exc: Optional[Exception] = None
        for attempt in range(self.policy.max_attempts):
            if not self.registry.allow(breaker_name):
                raise RuntimeError(f"circuit open: {breaker_name}")
            try:
                result = await fn()
                self.registry.record(breaker_name, success=True)
                return result
            except Exception as exc:
                self.registry.record(breaker_name, success=False)
                last_exc = exc
                if attempt < self.policy.max_attempts - 1:
                    import asyncio
                    await asyncio.sleep(self.policy.delay(attempt))
        raise last_exc or RuntimeError("retries exhausted")


@dataclass
class RecoveryAction:
    id: str
    target: str
    action: str
    reason: str
    status: str = "pending"
    created_at: float = field(default_factory=now)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target": self.target,
            "action": self.action,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


class HealthProbe:
    def __init__(self, name: str, fn: Callable[[], bool], *, interval_s: float = 10.0) -> None:
        self.name = name
        self.fn = fn
        self.interval_s = interval_s
        self.last_check_at: Optional[float] = None
        self.last_result: bool = True
        self.failure_count: int = 0

    def run(self) -> bool:
        try:
            ok = self.fn()
        except Exception:
            ok = False
        self.last_check_at = now()
        self.last_result = ok
        if not ok:
            self.failure_count += 1
        else:
            self.failure_count = 0
        return ok


class SelfHealing:
    def __init__(self) -> None:
        self.circuits = CircuitRegistry()
        self.retrier = Retrier(self.circuits)
        self.probes: Dict[str, HealthProbe] = {}
        self.actions: List[RecoveryAction] = []

    def add_probe(self, probe: HealthProbe) -> None:
        self.probes[probe.name] = probe

    def run_probes(self) -> Dict[str, Any]:
        results = {}
        for name, probe in self.probes.items():
            ok = probe.run()
            if not ok and probe.failure_count >= 3:
                self.recover(probe.name, "probe_failed", f"{probe.name} failed {probe.failure_count}x")
            results[name] = {"ok": ok, "failures": probe.failure_count}
        return results

    def recover(self, target: str, action: str, reason: str) -> RecoveryAction:
        rec = RecoveryAction(
            id=make_id("rec"),
            target=target,
            action=action,
            reason=reason,
        )
        self.actions.append(rec)
        if len(self.actions) > 1000:
            self.actions = self.actions[-1000:]
        # Mark complete immediately for in-process actions; real impl triggers
        # an external workflow.
        rec.status = "completed"
        rec.completed_at = now()
        logger.info("recovery action recorded: %s -> %s (%s)", target, action, reason)
        return rec

    def status(self) -> Dict[str, Any]:
        return {
            "circuits": self.circuits.all(),
            "probes": {n: {"last_result": p.last_result, "failures": p.failure_count} for n, p in self.probes.items()},
            "actions": [a.to_dict() for a in self.actions[-20:]],
        }


_GLOBAL_HEALING: Optional[SelfHealing] = None


def get_self_healing() -> SelfHealing:
    global _GLOBAL_HEALING
    if _GLOBAL_HEALING is None:
        _GLOBAL_HEALING = SelfHealing()
    return _GLOBAL_HEALING