import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.recursive_improvement import (
    RecursiveSelfImprover,
    ImprovementStep,
)


class TestRecursiveSelfImprover:
    def test_run_improvement_loop_returns_steps(self):
        improver = RecursiveSelfImprover(initial_capability=1.0, max_iterations=20)
        steps = improver.run_improvement_loop(n_iterations=10)
        assert len(steps) == 10
        assert all(isinstance(s, ImprovementStep) for s in steps)

    def test_capability_increases(self):
        improver = RecursiveSelfImprover(initial_capability=1.0, max_iterations=50)
        steps = improver.run_improvement_loop(n_iterations=20)
        assert steps[-1].capability_score > steps[0].capability_score

    def test_bootstrap_success(self):
        improver = RecursiveSelfImprover(initial_capability=1.0, improvement_rate=0.2, max_iterations=200)
        result = improver.bootstrap(target_capability=5.0)
        assert result["success"] == True
        assert result["final_capability"] >= 5.0

    def test_bootstrap_failure(self):
        improver = RecursiveSelfImprover(initial_capability=0.1, improvement_rate=0.001, max_iterations=5)
        result = improver.bootstrap(target_capability=100.0)
        assert result["success"] == False
        assert result["iterations_used"] <= 5

    def test_improvement_stats(self):
        improver = RecursiveSelfImprover()
        improver.run_improvement_loop(n_iterations=15)
        stats = improver.get_improvement_stats()
        assert stats["iterations"] == 15
        assert "final_capability" in stats
