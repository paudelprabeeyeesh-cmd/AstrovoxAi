from dataclasses import dataclass, field
from itertools import groupby
from typing import List, Dict, Optional


@dataclass
class ContextComponent:
    name: str
    tokens: int
    priority: int
    content: str = ""

    def __post_init__(self):
        if self.priority < 0:
            raise ValueError("priority must be non-negative")


PRIORITY_SYSTEM = 0
PRIORITY_TOOLS = 1
PRIORITY_CURRENT = 2
PRIORITY_RECENT = 3
PRIORITY_RETRIEVED = 4
PRIORITY_OLD = 5


class TokenBudgetAccountant:
    def __init__(self, budget: int):
        if budget < 0:
            raise ValueError("budget must be non-negative")
        self.budget = budget
        self.components: List[ContextComponent] = []

    def add_component(self, name: str, tokens: int, priority: int, content: str = "") -> None:
        if tokens < 0:
            raise ValueError("tokens must be non-negative")
        self.components.append(ContextComponent(name=name, tokens=tokens, priority=priority, content=content))

    def total_tokens(self) -> int:
        return sum(c.tokens for c in self.components)

    def overspend(self) -> int:
        return max(0, self.total_tokens() - self.budget)

    def trim(self) -> List[ContextComponent]:
        sorted_components = sorted(self.components, key=lambda c: c.priority)
        remaining = self.budget
        kept: List[ContextComponent] = []
        removed: List[ContextComponent] = []
        for priority, group in groupby(sorted_components, key=lambda c: c.priority):
            group_list = list(group)
            group_tokens = sum(c.tokens for c in group_list)
            if group_tokens <= remaining:
                kept.extend(group_list)
                remaining -= group_tokens
            else:
                removed.extend(group_list)
        self.components = kept
        return removed

    def component_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for c in self.components:
            counts[c.name] = counts.get(c.name, 0) + c.tokens
        return counts
