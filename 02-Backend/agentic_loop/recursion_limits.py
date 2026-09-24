import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class BudgetConfig:
    max_iterations: int = 10
    max_cost: float = 1.0
    max_time: float = 120.0
    cost_per_iteration: float = 0.01


@dataclass
class BudgetState:
    iterations: int = 0
    cost: float = 0.0
    start_time: float = field(default_factory=time.time)

    def elapsed_time(self) -> float:
        return time.time() - self.start_time


class RecursionLimiter:
    def __init__(self, config: Optional[BudgetConfig] = None):
        self.config = config or BudgetConfig()

    def check(self, state: BudgetState) -> tuple[bool, Optional[str]]:
        if state.iterations >= self.config.max_iterations:
            return False, f"iteration_limit_exceeded: {state.iterations}/{self.config.max_iterations}"
        if state.cost >= self.config.max_cost:
            return False, f"cost_budget_exceeded: {state.cost:.4f}/{self.config.max_cost}"
        if state.elapsed_time() >= self.config.max_time:
            return False, f"time_limit_exceeded: {state.elapsed_time():.2f}s/{self.config.max_time}s"
        return True, None

    def update(self, state: BudgetState) -> BudgetState:
        state.iterations += 1
        state.cost += self.config.cost_per_iteration
        return state

    def dynamic_budget(self, state: BudgetState, performance_score: float) -> BudgetConfig:
        factor = max(0.5, min(2.0, performance_score))
        return BudgetConfig(
            max_iterations=int(self.config.max_iterations * factor),
            max_cost=self.config.max_cost * factor,
            max_time=self.config.max_time * factor,
            cost_per_iteration=self.config.cost_per_iteration,
        )
