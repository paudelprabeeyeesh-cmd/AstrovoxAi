"""Error budgets with alerting."""

from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    alert_id: str
    budget_id: str
    severity: AlertSeverity
    message: str
    burn_rate: float
    budget_remaining: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


@dataclass
class ErrorBudget:
    budget_id: str
    slo_name: str
    target_slo: float
    window_days: int
    error_budget: float
    error_budget_remaining: float
    burn_rate: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    alerts: List[Alert] = field(default_factory=list)


class ErrorBudgetManager:
    _budgets: Dict[str, ErrorBudget] = {}
    _alert_handlers: List[Any] = []

    @classmethod
    def register_alert_handler(cls, handler: Any) -> None:
        cls._alert_handlers.append(handler)

    @classmethod
    def create_budget(cls, slo_name: str, target_slo: float, window_days: int = 30) -> ErrorBudget:
        error_budget = 1.0 - target_slo
        budget_id = f"eb_{slo_name}_{datetime.now(timezone.utc).timestamp()}"
        budget = ErrorBudget(
            budget_id=budget_id,
            slo_name=slo_name,
            target_slo=target_slo,
            window_days=window_days,
            error_budget=error_budget,
            error_budget_remaining=error_budget,
            burn_rate=0.0,
        )
        cls._budgets[slo_name] = budget
        return budget

    @classmethod
    def consume_budget(cls, slo_name: str, amount: float) -> bool:
        budget = cls._budgets.get(slo_name)
        if not budget:
            return False
        if budget.error_budget_remaining >= amount:
            budget.error_budget_remaining -= amount
            budget.burn_rate = (budget.error_budget - budget.error_budget_remaining) / (budget.window_days * 24 * 3600)
            cls._check_alerts(budget)
            return True
        return False

    @classmethod
    def is_budget_exhausted(cls, slo_name: str) -> bool:
        budget = cls._budgets.get(slo_name)
        return budget.error_budget_remaining <= 0 if budget else False

    @classmethod
    def get_burn_rate(cls, slo_name: str) -> float:
        budget = cls._budgets.get(slo_name)
        return budget.burn_rate if budget else 0.0

    @classmethod
    def get_remaining_percentage(cls, slo_name: str) -> float:
        budget = cls._budgets.get(slo_name)
        if not budget or budget.error_budget == 0:
            return 0.0
        return (budget.error_budget_remaining / budget.error_budget) * 100

    @classmethod
    def _check_alerts(cls, budget: ErrorBudget) -> None:
        remaining_pct = cls.get_remaining_percentage(budget.slo_name)
        severity = AlertSeverity.INFO
        if remaining_pct <= 0:
            severity = AlertSeverity.CRITICAL
        elif remaining_pct <= 10:
            severity = AlertSeverity.WARNING

        alert = Alert(
            alert_id=f"alert_{budget.budget_id}_{datetime.now(timezone.utc).timestamp()}",
            budget_id=budget.budget_id,
            severity=severity,
            message=f"Error budget for {budget.slo_name} is at {remaining_pct:.1f}%",
            burn_rate=budget.burn_rate,
            budget_remaining=budget.error_budget_remaining
        )
        budget.alerts.append(alert)

        for handler in cls._alert_handlers:
            try:
                handler(alert)
            except Exception:
                pass

    @classmethod
    def get_budget_health(cls) -> Dict[str, Dict[str, Any]]:
        health = {}
        for name, budget in cls._budgets.items():
            health[name] = {
                "slo_name": name,
                "remaining_pct": cls.get_remaining_percentage(name),
                "burn_rate": budget.burn_rate,
                "exhausted": cls.is_budget_exhausted(name),
                "alert_count": len(budget.alerts)
            }
        return health

    @classmethod
    def acknowledge_alert(cls, alert_id: str) -> bool:
        for budget in cls._budgets.values():
            for alert in budget.alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
        return False

    @classmethod
    def get_active_alerts(cls) -> List[Alert]:
        alerts = []
        for budget in cls._budgets.values():
            alerts.extend([a for a in budget.alerts if not a.acknowledged])
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

