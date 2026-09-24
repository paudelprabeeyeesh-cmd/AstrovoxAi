import time
import pytest
from agentic_loop.recursion_limits import (
    RecursionLimiter,
    BudgetConfig,
    BudgetState,
)


def test_iteration_limit():
    limiter = RecursionLimiter(BudgetConfig(max_iterations=2, max_cost=10, max_time=1000))
    state = BudgetState()
    ok, _ = limiter.check(state)
    assert ok
    limiter.update(state)
    ok, _ = limiter.check(state)
    assert ok
    limiter.update(state)
    ok, reason = limiter.check(state)
    assert not ok
    assert "iteration_limit_exceeded" in reason


def test_cost_limit():
    limiter = RecursionLimiter(BudgetConfig(max_iterations=100, max_cost=0.02, max_time=1000, cost_per_iteration=0.01))
    state = BudgetState()
    limiter.update(state)
    ok, _ = limiter.check(state)
    assert ok
    limiter.update(state)
    ok, reason = limiter.check(state)
    assert not ok
    assert "cost_budget_exceeded" in reason


def test_time_limit():
    limiter = RecursionLimiter(BudgetConfig(max_iterations=100, max_cost=10, max_time=0.1))
    state = BudgetState()
    time.sleep(0.15)
    ok, reason = limiter.check(state)
    assert not ok
    assert "time_limit_exceeded" in reason


def test_dynamic_budget():
    limiter = RecursionLimiter(BudgetConfig(max_iterations=10, max_cost=1.0, max_time=60.0))
    state = BudgetState()
    new_config = limiter.dynamic_budget(state, performance_score=1.5)
    assert new_config.max_iterations == 15
    assert new_config.max_cost == pytest.approx(1.5)


def test_budget_state_elapsed_time():
    state = BudgetState()
    time.sleep(0.05)
    assert state.elapsed_time() >= 0.05
