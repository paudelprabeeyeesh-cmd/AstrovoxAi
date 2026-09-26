"""Automated rollback based on SLO violations."""
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from .incident_manager import IncidentManager, IncidentSeverity


@dataclass
class RollbackPolicy:
    error_budget_fast_burn_threshold: float = 14.4
    error_budget_slow_burn_threshold: float = 3.0
    max_consecutive_failures: int = 3
    cooldown_seconds: int = 600


class AutomatedRollback:
    def __init__(
        self,
        policy: Optional[RollbackPolicy] = None,
        incident_manager: Optional[IncidentManager] = None,
        on_rollback: Optional[Callable[[str], None]] = None,
    ):
        self.policy = policy or RollbackPolicy()
        self.incident_manager = incident_manager or IncidentManager()
        self._on_rollback = on_rollback
        self._consecutive_failures = 0
        self._last_rollback = datetime.min.replace(tzinfo=timezone.utc)

    def evaluate(self, error_budget_remaining: float, burn_rate: float, healthy: bool) -> Optional[str]:
        if healthy:
            self._consecutive_failures = 0
            return None
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.policy.max_consecutive_failures:
            incident = self.incident_manager.create(
                title="Automated rollback triggered by health check",
                severity=IncidentSeverity.P1,
                description=f"Consecutive failures reached {self._consecutive_failures}",
                owner="automation",
            )
            self._execute_rollback(f"health_check_failure_{incident.id}")
            return incident.id
        if burn_rate >= self.policy.error_budget_fast_burn_threshold:
            incident = self.incident_manager.create(
                title="Automated rollback triggered by fast error budget burn",
                severity=IncidentSeverity.P1,
                description=f"Burn rate {burn_rate} exceeded threshold {self.policy.error_budget_fast_burn_threshold}",
                owner="automation",
            )
            self._execute_rollback(f"burn_rate_{incident.id}")
            return incident.id
        if error_budget_remaining <= 0.0 and burn_rate >= self.policy.error_budget_slow_burn_threshold:
            incident = self.incident_manager.create(
                title="Automated rollback triggered by error budget exhaustion",
                severity=IncidentSeverity.P2,
                description="Error budget exhausted with sustained burn rate",
                owner="automation",
            )
            self._execute_rollback(f"error_budget_{incident.id}")
            return incident.id
        return None

    def _execute_rollback(self, reason: str):
        now = datetime.now(timezone.utc)
        if (now - self._last_rollback).total_seconds() < self.policy.cooldown_seconds:
            return
        self._last_rollback = now
        if self._on_rollback:
            self._on_rollback(reason)
