"""Cost Management — token tracking, budgets, forecasting."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


# Cost per 1K tokens (USD)
MODEL_COSTS = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-1.0-pro": {"input": 0.0005, "output": 0.0015},
    "llama3": {"input": 0, "output": 0},
    "llama3.1": {"input": 0, "output": 0},
    "mistral": {"input": 0, "output": 0},
    "mixtral": {"input": 0, "output": 0},
    "codellama": {"input": 0, "output": 0},
    "phi3": {"input": 0, "output": 0},
    "gemma2": {"input": 0, "output": 0},
}


@dataclass
class TokenUsage:
    """Token usage record."""
    user_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: float


@dataclass
class Budget:
    """User or organization budget."""
    id: str
    name: str
    amount: float
    period: str
    current_usage: float = 0.0
    is_active: bool = True


class CostTracker:
    """Track and manage AI costs."""

    def __init__(self):
        self._usage: list[TokenUsage] = []
        self._user_usage: dict[str, list[TokenUsage]] = defaultdict(list)
        self._budgets: dict[str, Budget] = {}

    def record_usage(
        self,
        user_id: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
    ) -> TokenUsage:
        """Record token usage and calculate cost."""
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        usage = TokenUsage(
            user_id=user_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            timestamp=time.time(),
        )

        self._usage.append(usage)
        self._user_usage[user_id].append(usage)

        return usage

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a request."""
        costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        input_cost = costs["input"] * input_tokens / 1000
        output_cost = costs["output"] * output_tokens / 1000
        return round(input_cost + output_cost, 6)

    def get_user_usage(
        self,
        user_id: str,
        since: float = 0,
    ) -> list[TokenUsage]:
        """Get usage records for a user."""
        return [u for u in self._user_usage.get(user_id, []) if u.timestamp >= since]

    def get_user_total_cost(
        self,
        user_id: str,
        since: float = 0,
    ) -> float:
        """Get total cost for a user."""
        usage = self.get_user_usage(user_id, since)
        return sum(u.cost for u in usage)

    def get_daily_cost(self, user_id: str) -> float:
        """Get today's cost for a user."""
        start_of_day = time.time() - (time.time() % 86400)
        return self.get_user_total_cost(user_id, since=start_of_day)

    def get_monthly_cost(self, user_id: str) -> float:
        """Get this month's cost for a user."""
        start_of_month = time.time() - (time.time() % 2592000)
        return self.get_user_total_cost(user_id, since=start_of_month)

    def create_budget(
        self,
        name: str,
        amount: float,
        period: str = "monthly",
    ) -> Budget:
        """Create a budget."""
        import secrets
        budget = Budget(
            id=secrets.token_hex(8),
            name=name,
            amount=amount,
            period=period,
        )
        self._budgets[budget.id] = budget
        return budget

    def check_budget(self, budget_id: str, user_id: str) -> dict:
        """Check if a user is within budget."""
        budget = self._budgets.get(budget_id)
        if not budget:
            return {"valid": False, "reason": "Budget not found"}

        if budget.period == "daily":
            usage = self.get_daily_cost(user_id)
        elif budget.period == "monthly":
            usage = self.get_monthly_cost(user_id)
        else:
            usage = self.get_user_total_cost(user_id)

        remaining = budget.amount - usage
        percentage = (usage / budget.amount * 100) if budget.amount > 0 else 0

        return {
            "valid": remaining > 0,
            "budget_amount": budget.amount,
            "current_usage": round(usage, 4),
            "remaining": round(remaining, 4),
            "percentage": round(percentage, 2),
            "exceeded": remaining <= 0,
        }

    def get_provider_cost_comparison(self, user_id: str = None) -> dict:
        """Compare costs across providers."""
        usage_records = self._usage
        if user_id:
            usage_records = self._user_usage.get(user_id, [])

        provider_costs = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "requests": 0})
        for u in usage_records:
            provider_costs[u.provider]["cost"] += u.cost
            provider_costs[u.provider]["tokens"] += u.input_tokens + u.output_tokens
            provider_costs[u.provider]["requests"] += 1

        return dict(provider_costs)

    def get_cost_forecast(self, user_id: str, days: int = 30) -> dict:
        """Forecast future costs based on usage."""
        now = time.time()
        recent = self.get_user_usage(user_id, since=now - 604800)

        if not recent:
            return {"daily_average": 0, "forecast": 0, "trend": "stable"}

        total_cost = sum(u.cost for u in recent)
        daily_average = total_cost / 7

        return {
            "daily_average": round(daily_average, 4),
            "forecast": round(daily_average * days, 4),
            "trend": "stable",
        }

    def get_usage_report(self, user_id: str, days: int = 30) -> dict:
        """Generate a usage report."""
        since = time.time() - (days * 86400)
        usage = self.get_user_usage(user_id, since)

        total_input = sum(u.input_tokens for u in usage)
        total_output = sum(u.output_tokens for u in usage)
        total_cost = sum(u.cost for u in usage)

        model_usage = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0})
        for u in usage:
            model_usage[u.model]["tokens"] += u.input_tokens + u.output_tokens
            model_usage[u.model]["cost"] += u.cost
            model_usage[u.model]["requests"] += 1

        return {
            "period_days": days,
            "total_requests": len(usage),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost": round(total_cost, 4),
            "model_breakdown": dict(model_usage),
        }


cost_tracker = CostTracker()
