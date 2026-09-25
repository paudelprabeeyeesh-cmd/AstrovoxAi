"""Token budget enforcement."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TokenBudget:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float


class TokenBudgetEnforcer:
    def __init__(self, max_tokens_per_request: int = 100_000, max_cost_per_request: float = 1.0) -> None:
        self.max_tokens_per_request = max_tokens_per_request
        self.max_cost_per_request = max_cost_per_request

    def check(self, budget: TokenBudget) -> None:
        if budget.total_tokens > self.max_tokens_per_request:
            raise ValueError(f"Token budget exceeded: {budget.total_tokens} > {self.max_tokens_per_request}")
        if budget.cost > self.max_cost_per_request:
            raise ValueError(f"Cost budget exceeded: ${budget.cost:.4f} > ${self.max_cost_per_request}")
