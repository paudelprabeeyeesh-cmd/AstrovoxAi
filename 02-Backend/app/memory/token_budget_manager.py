"""Token budget management for context windows."""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class BudgetPriority(Enum):
    SYSTEM = 4
    RECENT = 3
    RELEVANT = 2
    HISTORICAL = 1


@dataclass
class BudgetAllocation:
    category: str
    priority: BudgetPriority
    reserved_tokens: int
    used_tokens: int = 0
    max_tokens: int = 0

    def remaining(self) -> int:
        return max(0, self.reserved_tokens - self.used_tokens)

    def can_use(self, tokens: int) -> bool:
        return (self.used_tokens + tokens) <= self.reserved_tokens


class TokenBudgetManager:
    def __init__(self, total_budget: int = 8192):
        self.total_budget = total_budget
        self.allocations: Dict[str, BudgetAllocation] = {}
        self.allocate(BudgetAllocation(
            category="system",
            priority=BudgetPriority.SYSTEM,
            reserved_tokens=int(total_budget * 0.15),
            max_tokens=total_budget,
        ))
        self.allocate(BudgetAllocation(
            category="recent",
            priority=BudgetPriority.RECENT,
            reserved_tokens=int(total_budget * 0.35),
            max_tokens=total_budget,
        ))
        self.allocate(BudgetAllocation(
            category="relevant",
            priority=BudgetPriority.RELEVANT,
            reserved_tokens=int(total_budget * 0.30),
            max_tokens=total_budget,
        ))
        self.allocate(BudgetAllocation(
            category="historical",
            priority=BudgetPriority.HISTORICAL,
            reserved_tokens=int(total_budget * 0.20),
            max_tokens=total_budget,
        ))

    def allocate(self, allocation: BudgetAllocation) -> None:
        self.allocations[allocation.category] = allocation

    def use(self, category: str, tokens: int) -> bool:
        allocation = self.allocations.get(category)
        if allocation and allocation.can_use(tokens):
            allocation.used_tokens += tokens
            return True
        return False

    def remaining(self, category: str) -> int:
        allocation = self.allocations.get(category)
        return allocation.remaining() if allocation else 0

    def total_remaining(self) -> int:
        return sum(a.remaining() for a in self.allocations.values())

    def get_allocation(self, category: str) -> Optional[BudgetAllocation]:
        return self.allocations.get(category)
