import numpy as np
import pytest
from ..creative_problem_solving import CreativeProblemSolving


class TestCreativeProblemSolving:
    def test_divergent_thinking(self):
        cps = CreativeProblemSolving()
        ideas = cps.divergent_thinking("solve problem", n_ideas=5)
        assert len(ideas) == 5
        assert all("originality" in idea for idea in ideas)

    def test_converge_solutions(self):
        cps = CreativeProblemSolving()
        ideas = cps.divergent_thinking("problem", n_ideas=3)
        converged = cps.converge_solutions(ideas, iterations=2)
        assert len(converged) > 0

    def test_analogical_transfer(self):
        cps = CreativeProblemSolving()
        result = cps.analogical_transfer("biology", "engineering")
        assert result["source"] == "biology"
        assert result["target"] == "engineering"
        assert "mapping" in result

    def test_innovation_score(self):
        cps = CreativeProblemSolving()
        score = cps.get_innovation_score({"originality": 0.9, "feasibility": 0.8})
        assert 0.0 <= score <= 1.0

    def test_innovation_score_clamping(self):
        cps = CreativeProblemSolving()
        score = cps.get_innovation_score({"originality": 2.0, "feasibility": -1.0})
        assert 0.0 <= score <= 1.0

    def test_divergent_originality_range(self):
        cps = CreativeProblemSolving(divergence_factor=0.5)
        ideas = cps.divergent_thinking("x", n_ideas=10)
        for idea in ideas:
            assert 0.0 <= idea["originality"] <= 1.0
