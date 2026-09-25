"""Error budgets."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta


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


class ErrorBudgetManager:
    _budgets: Dict[str, ErrorBudget] = {}

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
            return True
        return False

    @classmethod
    def is_budget_exhausted(cls, slo_name: str) -> bool:
        budget = cls._budgets.get(slo_name)
        return budget.error_budget_remaining <= 0 if budget else False
