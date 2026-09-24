import numpy as np
import pytest
from emergent_abilities.chain_of_thought import ChainOfThoughtModel, ReasoningScalingAnalyzer


class TestChainOfThoughtModel:
    def test_generate_chain_output(self):
        model = ChainOfThoughtModel(vocab_size=100, hidden_dim=32, max_steps=5)
        result = model.generate_chain(prompt_tokens=[1, 2, 3], max_new_tokens=3)
        assert len(result.reasoning_chain) > 0
        assert result.num_steps > 0
        assert result.num_steps <= 5

    def test_generate_chain_confidence(self):
        model = ChainOfThoughtModel(vocab_size=100, hidden_dim=32, max_steps=5)
        result = model.generate_chain(prompt_tokens=[1, 2, 3])
        assert 0.0 <= result.confidence <= 1.0

    def test_compute_scaling_law(self):
        model = ChainOfThoughtModel(vocab_size=100, hidden_dim=32)
        lengths = [10, 50, 100, 500, 1000]
        scaling = model.compute_scaling_law(prompt_lengths=lengths, num_runs=3)
        assert "intercept" in scaling
        assert "scaling_exponent" in scaling
        assert scaling["scaling_exponent"] != 0.0

    def test_empty_prompt(self):
        model = ChainOfThoughtModel(vocab_size=100, hidden_dim=16, max_steps=3)
        result = model.generate_chain(prompt_tokens=[])
        assert result.num_steps <= 3


class TestReasoningScalingAnalyzer:
    def test_record_step_performance(self):
        analyzer = ReasoningScalingAnalyzer()
        analyzer.record_step_performance(num_steps=5, performance=0.8)
        assert len(analyzer.step_performance[5]) == 1

    def test_scaling_curve(self):
        analyzer = ReasoningScalingAnalyzer()
        for steps in range(1, 17):
            analyzer.record_step_performance(steps, float(steps) / 16.0)
        curve = analyzer.scaling_curve()
        assert len(curve) == 16

    def test_diminishing_returns_point(self):
        analyzer = ReasoningScalingAnalyzer()
        for steps in range(1, 17):
            analyzer.record_step_performance(steps, float(steps) / 16.0)
        point = analyzer.diminishing_returns_point()
        assert point is None

    def test_diminishing_returns_with_increase(self):
        analyzer = ReasoningScalingAnalyzer()
        perfs = [0.1, 0.3, 0.4, 0.42, 0.425] + [0.425] * 12
        for steps, perf in enumerate(perfs, start=1):
            analyzer.record_step_performance(steps, perf)
        point = analyzer.diminishing_returns_point()
        assert point is not None
        assert point >= 3
