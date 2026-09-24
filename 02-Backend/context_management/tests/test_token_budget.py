import pytest
import numpy as np
from context_management.token_budget import (
    TokenBudgetAccountant,
    ContextComponent,
    PRIORITY_SYSTEM,
    PRIORITY_TOOLS,
    PRIORITY_CURRENT,
    PRIORITY_RECENT,
    PRIORITY_RETRIEVED,
    PRIORITY_OLD,
)


class TestTokenBudgetAccountant:
    def test_add_component(self):
        accountant = TokenBudgetAccountant(budget=100)
        accountant.add_component("system", 20, PRIORITY_SYSTEM)
        assert accountant.total_tokens() == 20

    def test_total_tokens(self):
        accountant = TokenBudgetAccountant(budget=100)
        accountant.add_component("system", 20, PRIORITY_SYSTEM)
        accountant.add_component("tools", 30, PRIORITY_TOOLS)
        assert accountant.total_tokens() == 50

    def test_overspend_zero_when_under_budget(self):
        accountant = TokenBudgetAccountant(budget=100)
        accountant.add_component("system", 20, PRIORITY_SYSTEM)
        assert accountant.overspend() == 0

    def test_overspend_positive_when_over_budget(self):
        accountant = TokenBudgetAccountant(budget=100)
        accountant.add_component("system", 150, PRIORITY_SYSTEM)
        assert accountant.overspend() == 50

    def test_trim_removes_lowest_priority_first(self):
        accountant = TokenBudgetAccountant(budget=30)
        accountant.add_component("old", 20, PRIORITY_OLD)
        accountant.add_component("system", 10, PRIORITY_SYSTEM)
        accountant.add_component("retrieved", 15, PRIORITY_RETRIEVED)
        removed = accountant.trim()
        assert len(removed) == 1
        assert removed[0].name == "old"
        assert accountant.total_tokens() == 25

    def test_trim_keeps_highest_priority(self):
        accountant = TokenBudgetAccountant(budget=30)
        accountant.add_component("system", 10, PRIORITY_SYSTEM)
        accountant.add_component("tools", 15, PRIORITY_TOOLS)
        accountant.add_component("old", 20, PRIORITY_OLD)
        removed = accountant.trim()
        kept_names = {c.name for c in accountant.components}
        assert "system" in kept_names
        assert "tools" in kept_names
        assert "old" not in kept_names

    def test_trim_empty_components(self):
        accountant = TokenBudgetAccountant(budget=0)
        removed = accountant.trim()
        assert removed == []

    def test_component_counts(self):
        accountant = TokenBudgetAccountant(budget=100)
        accountant.add_component("system", 10, PRIORITY_SYSTEM)
        accountant.add_component("system", 20, PRIORITY_SYSTEM)
        accountant.add_component("tools", 30, PRIORITY_TOOLS)
        counts = accountant.component_counts()
        assert counts["system"] == 30
        assert counts["tools"] == 30

    def test_negative_budget_raises(self):
        with pytest.raises(ValueError):
            TokenBudgetAccountant(budget=-1)

    def test_negative_tokens_raises(self):
        accountant = TokenBudgetAccountant(budget=100)
        with pytest.raises(ValueError):
            accountant.add_component("system", -10, PRIORITY_SYSTEM)

    def test_trim_multiple_same_priority(self):
        accountant = TokenBudgetAccountant(budget=20)
        accountant.add_component("a", 10, PRIORITY_OLD)
        accountant.add_component("b", 10, PRIORITY_OLD)
        accountant.add_component("c", 5, PRIORITY_SYSTEM)
        removed = accountant.trim()
        assert len(removed) == 2
        kept_names = {c.name for c in accountant.components}
        assert kept_names == {"c"}

    def test_priority_order_system_to_old(self):
        accountant = TokenBudgetAccountant(budget=100)
        accountant.add_component("system", 30, PRIORITY_SYSTEM)
        accountant.add_component("tools", 30, PRIORITY_TOOLS)
        accountant.add_component("current", 30, PRIORITY_CURRENT)
        accountant.add_component("recent", 30, PRIORITY_RECENT)
        accountant.add_component("retrieved", 30, PRIORITY_RETRIEVED)
        accountant.add_component("old", 30, PRIORITY_OLD)
        removed = accountant.trim()
        assert len(removed) == 3
        kept_names = {c.name for c in accountant.components}
        assert kept_names == {"system", "tools", "current"}

    def test_numpy_random_budget_trim(self):
        np.random.seed(42)
        for _ in range(50):
            budget = int(np.random.randint(1, 200))
            accountant = TokenBudgetAccountant(budget=budget)
            num_components = int(np.random.randint(3, 10))
            for i in range(num_components):
                tokens = int(np.random.randint(1, 50))
                priority = int(np.random.randint(0, 6))
                accountant.add_component(f"comp-{i}", tokens, priority)
            removed = accountant.trim()
            assert accountant.total_tokens() <= budget
            assert len(accountant.components) + len(removed) == num_components
