import pytest
import numpy as np
from agi_core.autonomous_agency import AutonomousAgency


class TestAutonomousAgency:
    def test_set_goal(self):
        agent = AutonomousAgency()
        state = agent.set_goal("explore", 0.9)
        assert state.goal == "explore"
        assert state.autono_level == 0.9

    def test_choose_action(self):
        agent = AutonomousAgency()
        agent.set_goal("g")
        state = agent.choose_action(["a", "b", "c"])
        assert state.action in ["a", "b", "c"]
        assert 0.0 <= state.confidence <= 1.0

    def test_self_direct(self):
        agent = AutonomousAgency()
        agent.set_goal("g")
        state = agent.self_direct("good")
        assert state.confidence >= 0.5

    def test_evaluate_agency(self):
        agent = AutonomousAgency()
        agent.set_goal("test")
        report = agent.evaluate_agency()
        assert "goal_clarity" in report
        assert "autonomy" in report

    def test_goal_history(self):
        agent = AutonomousAgency()
        agent.set_goal("g1")
        agent.set_goal("g2")
        assert len(agent.goal_history) == 2
