from context_management.token_budget import TokenBudgetAccountant, PRIORITY_SYSTEM, PRIORITY_RETRIEVED


def test_init_non_negative_budget():
    for invalid in (-1, -10):
        try:
            TokenBudgetAccountant(budget=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_add_component():
    accountant = TokenBudgetAccountant(budget=100)
    accountant.add_component("system", 10, PRIORITY_SYSTEM)
    assert accountant.total_tokens() == 10


def test_add_component_negative_tokens():
    accountant = TokenBudgetAccountant(budget=100)
    try:
        accountant.add_component("system", -1, PRIORITY_SYSTEM)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_total_tokens():
    accountant = TokenBudgetAccountant(budget=100)
    accountant.add_component("a", 10, 0)
    accountant.add_component("b", 20, 1)
    assert accountant.total_tokens() == 30


def test_overspend():
    accountant = TokenBudgetAccountant(budget=10)
    accountant.add_component("a", 20, 0)
    assert accountant.overspend() == 10


def test_no_overspend():
    accountant = TokenBudgetAccountant(budget=100)
    accountant.add_component("a", 20, 0)
    assert accountant.overspend() == 0


def test_trim_removes_highest_priority():
    accountant = TokenBudgetAccountant(budget=20)
    accountant.add_component("low", 15, PRIORITY_RETRIEVED)
    accountant.add_component("high", 10, PRIORITY_SYSTEM)
    removed = accountant.trim()
    assert len(removed) == 1
    assert removed[0].name == "low"


def test_trim_keeps_within_budget():
    accountant = TokenBudgetAccountant(budget=100)
    accountant.add_component("a", 30, 0)
    accountant.add_component("b", 40, 1)
    removed = accountant.trim()
    assert len(removed) == 0
    assert accountant.total_tokens() == 70


def test_component_counts():
    accountant = TokenBudgetAccountant(budget=100)
    accountant.add_component("a", 30, 0)
    accountant.add_component("b", 20, 0)
    counts = accountant.component_counts()
    assert counts["a"] == 30
    assert counts["b"] == 20
