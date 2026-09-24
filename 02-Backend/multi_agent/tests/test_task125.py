import numpy as np
import pytest
from multi_agent.task125_debate import Agent, DebateOrchestrator


class TestDebateOrchestrator:
    def test_run_debate_converges(self):
        orchestrator = DebateOrchestrator(convergence_threshold=1e-3, max_rounds=10)
        a = Agent("a")
        b = Agent("b")
        orchestrator.register(a)
        orchestrator.register(b)
        a.propose(np.array([1.0, 1.0]))
        b.propose(np.array([1.0, 1.0]))
        result = orchestrator.run_debate()
        assert result["converged"] == True
        assert result["rounds"] <= 10

    def test_run_debate_no_convergence(self):
        orchestrator = DebateOrchestrator(convergence_threshold=1e-10, max_rounds=3)
        a = Agent("a")
        b = Agent("b")
        orchestrator.register(a)
        orchestrator.register(b)
        a.propose(np.array([0.0, 0.0]))
        b.propose(np.array([10.0, 10.0]))
        result = orchestrator.run_debate()
        assert result["rounds"] == 2

    def test_critique_recording(self):
        a = Agent("a")
        b = Agent("b")
        a.critique(b, "needs improvement")
        assert b.critiques == ["needs improvement"]
