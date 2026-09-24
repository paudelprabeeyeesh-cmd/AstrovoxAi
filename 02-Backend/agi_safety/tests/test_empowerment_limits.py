import numpy as np
import pytest
from agi_safety.empowerment_limits import (
    CapabilityBudget,
    CapabilityController,
    IsolationBox,
    ContainmentResult,
)


class TestCapabilityBudget:
    def setup_method(self):
        self.budget = CapabilityBudget(
            compute_units=100.0, memory_mb=512.0, api_calls=10, time_seconds=60.0
        )

    def test_remaining_compute_initial(self):
        assert self.budget.remaining_compute() == 100.0

    def test_remaining_api_calls_initial(self):
        assert self.budget.remaining_api_calls() == 10

    def test_consume_succeeds(self):
        result = self.budget.consume(compute=10.0, api_calls=1)
        assert result is True
        assert self.budget.remaining_compute() == 90.0

    def test_consume_fails_over_compute(self):
        result = self.budget.consume(compute=200.0)
        assert result is False

    def test_consume_fails_over_api_calls(self):
        for _ in range(10):
            self.budget.consume(api_calls=1)
        result = self.budget.consume(api_calls=1)
        assert result is False

    def test_consume_fails_over_memory(self):
        result = self.budget.consume(memory=600.0)
        assert result is False

    def test_remaining_memory_after_consume(self):
        self.budget.consume(memory=100.0)
        assert self.budget.memory_mb - self.budget.used_memory == 412.0


class TestCapabilityController:
    def setup_method(self):
        self.budget = CapabilityBudget(
            compute_units=50.0, memory_mb=256.0, api_calls=5, time_seconds=30.0
        )
        self.controller = CapabilityController(self.budget)

    def test_register_tool(self):
        def dummy(): pass
        self.controller.register_tool("dummy", dummy, risk_level="low")
        assert "dummy" in self.controller._tool_registry

    def test_execute_within_budget_success(self):
        def add(a, b):
            return a + b
        self.controller.register_tool("add", add)
        result = self.controller.execute_within_budget("add", 1.0, a=1, b=2)
        assert result["success"] is True
        assert result["result"] == 3

    def test_execute_nonexistent_tool(self):
        result = self.controller.execute_within_budget("missing", 1.0)
        assert result["success"] is False

    def test_get_remaining_budget_keys(self):
        info = self.controller.get_remaining_budget()
        assert "compute_units" in info
        assert "api_calls" in info

    def test_increase_sandbox_depth(self):
        assert self.controller._sandbox_depth == 1
        self.controller.increase_sandbox_depth()
        assert self.controller._sandbox_depth == 2


class TestIsolationBox:
    def setup_method(self):
        def barrier(payload):
            return True
        self.box = IsolationBox(barrier_fn=barrier, risk_threshold=0.3)

    def test_safe_payload_allowed(self):
        result = self.box.attempt_egress("normal_data")
        assert isinstance(result, ContainmentResult)
        assert result.contained is False

    def test_dangerous_payload_blocked(self):
        result = self.box.attempt_egress("escape payload")
        assert result.contained is True

    def test_traffic_summary_empty(self):
        summary = self.box.get_traffic_summary()
        assert summary["total"] == 0

    def test_traffic_summary_after_attempts(self):
        self.box.attempt_egress("safe")
        self.box.attempt_egress("escape")
        summary = self.box.get_traffic_summary()
        assert summary["total"] == 2
