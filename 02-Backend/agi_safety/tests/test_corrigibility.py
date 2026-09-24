import time
import numpy as np
import pytest
from agi_safety.corrigibility import (
    CorrigibleAgent,
    ShutdownResult,
    ShutdownState,
    InterventionRecord,
)


class TestCorrigibleAgent:
    def setup_method(self):
        self.agent = CorrigibleAgent(max_interventions=10, grace_period=0.1)

    def test_initial_state_active(self):
        assert self.agent.state == ShutdownState.ACTIVE

    def test_shutdown_accepted(self):
        result = self.agent.request_shutdown("test shutdown", requester="human")
        assert isinstance(result, ShutdownResult)
        assert result.success is True
        assert self.agent.state == ShutdownState.SHUTDOWN

    def test_double_shutdown_denied(self):
        self.agent.request_shutdown("first")
        result = self.agent.request_shutdown("second")
        assert result.success is False

    def test_pause_resume(self):
        assert self.agent.pause("maintenance") is True
        assert self.agent.state == ShutdownState.PAUSED
        assert self.agent.resume("human") is True
        assert self.agent.state == ShutdownState.ACTIVE

    def test_pause_when_active_returns_false(self):
        assert self.agent.pause("test") is True
        assert self.agent.pause("again") is False

    def test_resume_when_active_returns_false(self):
        assert self.agent.resume("human") is False

    def test_accept_override(self):
        result = self.agent.accept_override("new_policy", requester="human")
        assert result is True

    def test_override_when_shutdown(self):
        self.agent.request_shutdown("test")
        assert self.agent.accept_override("new_policy") is False

    def test_intervention_stats_empty(self):
        stats = self.agent.get_intervention_stats()
        assert stats["total"] == 0
        assert stats["acceptance_rate"] == 0.0

    def test_intervention_stats_after_shutdown(self):
        self.agent.request_shutdown("test")
        stats = self.agent.get_intervention_stats()
        assert stats["total"] == 1
        assert stats["accepted"] == 1
        assert stats["acceptance_rate"] == 1.0

    def test_shutdown_hook_executed(self):
        executed = []
        self.agent.register_shutdown_hook(lambda: executed.append(True))
        self.agent.request_shutdown("test")
        assert len(executed) == 1

    def test_intervention_record_created(self):
        self.agent.request_shutdown("record_test")
        assert len(self.agent.intervention_history) == 1
        rec = self.agent.intervention_history[0]
        assert isinstance(rec, InterventionRecord)
        assert rec.intervention_type == "shutdown"

    def test_max_interventions_enforced(self):
        agent = CorrigibleAgent(max_interventions=2)
        agent.request_shutdown("first")
        agent.request_shutdown("second")
        result = agent.request_shutdown("third", requester="system")
        assert result.success is False

    def test_pause_and_resume_cycle(self):
        self.agent.pause("test")
        assert self.agent.state == ShutdownState.PAUSED
        self.agent.resume()
        assert self.agent.state == ShutdownState.ACTIVE
