import numpy as np
import pytest
from emergent_abilities.mathematical_reasoning import MathematicalReasoningModel, MathReasoningEmergenceAnalyzer, MathProblemResult


class TestMathematicalReasoningModel:
    def test_solve_output(self):
        model = MathematicalReasoningModel(vocab_size=100, hidden_dim=32, max_reasoning_steps=5)
        result = model.solve(problem_tokens=[1, 2, 3, 4, 5])
        assert isinstance(result, MathProblemResult)
        assert result.reasoning_steps > 0
        assert result.reasoning_steps <= 5

    def test_solve_confidence_range(self):
        model = MathematicalReasoningModel(vocab_size=100, hidden_dim=32, max_reasoning_steps=3)
        result = model.solve(problem_tokens=[1, 2])
        assert 0.0 <= result.confidence <= 1.0

    def test_embed_problem_empty(self):
        model = MathematicalReasoningModel(vocab_size=100, hidden_dim=16, max_reasoning_steps=3)
        emb = model.embed_problem(problem_tokens=[])
        assert emb.shape == (16,)
        assert np.allclose(emb, 0.0)

    def test_emergence_curve(self):
        model = MathematicalReasoningModel(vocab_size=100, hidden_dim=32, max_reasoning_steps=5)
        model_sizes = np.array([1e8, 1e9, 1e10, 1e11])
        complexities = np.array([0.2, 0.5, 0.8, 1.0])
        curve = model.emergence_curve(model_sizes, complexities)
        assert len(curve) == 4
        assert np.all((curve >= 0.0) & (curve <= 1.0))


class TestMathReasoningEmergenceAnalyzer:
    def test_record_result(self):
        analyzer = MathReasoningEmergenceAnalyzer()
        model = MathematicalReasoningModel(vocab_size=100, hidden_dim=16, max_reasoning_steps=3)
        result = model.solve(problem_tokens=[1, 2])
        analyzer.record_result(result, complexity_bin="easy")
        assert len(analyzer.results) == 1
        assert len(analyzer.complexity_bins["easy"]) == 1

    def test_emergence_by_complexity(self):
        analyzer = MathReasoningEmergenceAnalyzer()
        model = MathematicalReasoningModel(vocab_size=100, hidden_dim=16, max_reasoning_steps=3)
        for bin_name in ["easy", "medium", "hard"]:
            result = model.solve(problem_tokens=[1, 2, 3])
            analyzer.record_result(result, complexity_bin=bin_name)
        emergence = analyzer.emergence_by_complexity()
        assert set(emergence.keys()) == {"easy", "medium", "hard"}
        assert all(0.0 <= v <= 1.0 for v in emergence.values())

    def test_reasoning_depth_vs_accuracy(self):
        analyzer = MathReasoningEmergenceAnalyzer()
        model = MathematicalReasoningModel(vocab_size=100, hidden_dim=16, max_reasoning_steps=5)
        for _ in range(10):
            result = model.solve(problem_tokens=[1, 2, 3, 4])
            analyzer.record_result(result)
        depth_acc = analyzer.reasoning_depth_vs_accuracy()
        assert len(depth_acc) > 0

    def test_empty_analyzer(self):
        analyzer = MathReasoningEmergenceAnalyzer()
        emergence = analyzer.emergence_by_complexity()
        assert all(v == 0.0 for v in emergence.values())
