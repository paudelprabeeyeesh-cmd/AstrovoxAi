import random
import pytest
from emergent_abilities.chain_of_thought_emergence import (
    ChainOfThoughtModel,
    CoTResult,
    ReasoningScalingAnalyzer,
    _dot,
    _matmul_vec,
    _softmax,
    _tanh_vec,
    _transpose,
)


class TestHelpers:
    def test_dot_product(self):
        assert _dot([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]) == pytest.approx(32.0)

    def test_softmax_sum(self):
        result = _softmax([0.0, 1.0, 2.0])
        assert abs(sum(result) - 1.0) < 1e-6

    def test_tanh_bounds(self):
        vals = _tanh_vec([0.0, 10.0, -10.0])
        assert all(-1.0 <= v <= 1.0 for v in vals)
        assert _tanh_vec([0.0]) == [pytest.approx(0.0)]

    def test_transpose(self):
        m = [[1.0, 2.0], [3.0, 4.0]]
        assert _transpose(m) == [[1.0, 3.0], [2.0, 4.0]]

    def test_matmul_vec(self):
        matrix = [[1.0, 2.0], [3.0, 4.0]]
        result = _matmul_vec(matrix, [1.0, 1.0])
        assert result == pytest.approx([3.0, 7.0])


class TestCoTResult:
    def test_creation(self):
        r = CoTResult(
            reasoning_chain=["Step 1: a", "Step 2: b"],
            answer="token_5",
            confidence=0.85,
            num_steps=2,
            coherence_score=0.80,
        )
        assert r.num_steps == 2
        assert r.answer == "token_5"
        assert 0.0 <= r.confidence <= 1.0
        assert 0.0 <= r.coherence_score <= 1.0


class TestChainOfThoughtModel:
    def test_initialization(self):
        model = ChainOfThoughtModel(vocab_size=200, hidden_dim=32, max_steps=6)
        assert model.vocab_size == 200
        assert model.hidden_dim == 32
        assert model.max_steps == 6

    def test_embed_token(self):
        model = ChainOfThoughtModel(vocab_size=100, hidden_dim=8)
        emb = model.embed_token(5)
        assert len(emb) == 8

    def test_embed_token_oob(self):
        model = ChainOfThoughtModel(vocab_size=10, hidden_dim=4)
        emb = model.embed_token(9999)
        assert len(emb) == 4

    def test_generate_chain_empty_prompt(self):
        model = ChainOfThoughtModel(vocab_size=50, hidden_dim=8)
        result = model.generate_chain([], max_new_tokens=3)
        assert isinstance(result, CoTResult)
        assert len(result.reasoning_chain) <= model.max_steps
        assert result.num_steps == len(result.reasoning_chain)
        assert result.answer.startswith("token_")

    def test_generate_chain_with_prompt(self):
        random.seed(0)
        model = ChainOfThoughtModel(vocab_size=100, hidden_dim=16)
        result = model.generate_chain([1, 2, 3], max_new_tokens=5)
        assert result.num_steps >= 1
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.coherence_score <= 1.0

    def test_generate_chain_max_tokens(self):
        model = ChainOfThoughtModel(vocab_size=50, hidden_dim=8, max_steps=10)
        result = model.generate_chain([0], max_new_tokens=3)
        assert result.num_steps == 3

    def test_generate_chain_max_steps_respected(self):
        model = ChainOfThoughtModel(vocab_size=50, hidden_dim=8, max_steps=4)
        result = model.generate_chain([0], max_new_tokens=0)
        assert result.num_steps <= 4

    def test_compute_scaling_law(self):
        model = ChainOfThoughtModel(vocab_size=50, hidden_dim=8)
        lengths = [2, 4, 8, 16, 32]
        result = model.compute_scaling_law(lengths, num_runs=3)
        assert "intercept" in result
        assert "scaling_exponent" in result
        assert isinstance(result["intercept"], float)
        assert isinstance(result["scaling_exponent"], float)


class TestReasoningScalingAnalyzer:
    def test_initialization(self):
        analyzer = ReasoningScalingAnalyzer()
        assert 1 in analyzer.step_performance
        assert 16 in analyzer.step_performance

    def test_record_step_performance(self):
        analyzer = ReasoningScalingAnalyzer()
        analyzer.record_step_performance(5, 0.8)
        analyzer.record_step_performance(5, 0.9)
        assert len(analyzer.step_performance[5]) == 2

    def test_scaling_curve_empty(self):
        analyzer = ReasoningScalingAnalyzer()
        curve = analyzer.scaling_curve()
        assert len(curve) == 16
        assert all(v == 0.0 for v in curve)

    def test_scaling_curve_with_data(self):
        analyzer = ReasoningScalingAnalyzer()
        analyzer.record_step_performance(3, 0.6)
        analyzer.record_step_performance(3, 0.8)
        curve = analyzer.scaling_curve()
        assert curve[2] == pytest.approx(0.7)

    def test_diminishing_returns_none(self):
        analyzer = ReasoningScalingAnalyzer()
        result = analyzer.diminishing_returns_point()
        assert result is None

    def test_diminishing_returns_detected(self):
        analyzer = ReasoningScalingAnalyzer()
        for i in range(1, 10):
            analyzer.record_step_performance(i, max(0.95 - i * 0.05, 0.3))
        result = analyzer.diminishing_returns_point()
        assert result is not None
        assert 1 <= result <= 9

    def test_diminishing_returns_flat(self):
        analyzer = ReasoningScalingAnalyzer()
        for i in range(1, 10):
            analyzer.record_step_performance(i, 0.5)
        result = analyzer.diminishing_returns_point()
        assert result == 2
