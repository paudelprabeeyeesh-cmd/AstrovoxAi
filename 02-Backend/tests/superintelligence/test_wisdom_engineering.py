import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.wisdom_engineering import (
    WisdomEngineer,
    WisdomJudgment,
)


class TestWisdomEngineer:
    def test_train_calibration_returns_mse(self):
        eng = WisdomEngineer()
        outcomes = np.random.randn(50)
        decisions = np.random.randn(50)
        mse = eng.train_calibration(outcomes, decisions)
        assert isinstance(mse, float)
        assert mse >= 0.0

    def test_render_judgment(self):
        eng = WisdomEngineer()
        context = np.random.randn(64)
        options = [np.random.randn(64) for _ in range(3)]
        judgment = eng.render_judgment(context, options, horizon=5)
        assert isinstance(judgment, WisdomJudgment)
        assert 0.0 <= judgment.decision_quality <= 1.0
        assert 0.0 <= judgment.ethical_alignment <= 1.0
        assert len(judgment.explanation) > 0

    def test_render_judgment_bounds(self):
        eng = WisdomEngineer()
        context = np.random.randn(64)
        options = [np.random.randn(64) for _ in range(3)]
        for _ in range(20):
            judgment = eng.render_judgment(context, options, horizon=10)
            assert judgment.uncertainty >= 0.0

    def test_wisdom_stats(self):
        eng = WisdomEngineer()
        context = np.random.randn(64)
        options = [np.random.randn(64) for _ in range(3)]
        eng.render_judgment(context, options)
        stats = eng.get_wisdom_stats()
        assert stats["judgments_rendered"] == 1
        assert stats["trained"] is False

    def test_train_calibration_shape_mismatch(self):
        eng = WisdomEngineer()
        with pytest.raises(ValueError):
            eng.train_calibration(np.random.randn(10), np.random.randn(5))

    def test_evaluate_option_returns_float(self):
        eng = WisdomEngineer()
        context = np.random.randn(64)
        option = np.random.randn(64)
        score = eng._evaluate_option(context, option, horizon=5)
        assert isinstance(score, float)

    def test_estimate_uncertainty_single_score(self):
        eng = WisdomEngineer()
        uncertainty = eng._estimate_uncertainty([0.5])
        assert uncertainty == 0.5

    def test_generate_explanation_low_quality(self):
        eng = WisdomEngineer()
        explanation = eng._generate_explanation(0.2, 0.3, 0.4, 0.6)
        assert "low quality decision" in explanation

    def test_generate_explanation_high_quality(self):
        eng = WisdomEngineer()
        explanation = eng._generate_explanation(0.9, 0.8, 0.7, 0.1)
        assert "high quality decision" in explanation

    def test_wisdom_stats_empty(self):
        eng = WisdomEngineer()
        stats = eng.get_wisdom_stats()
        assert stats["judgments_rendered"] == 0
        assert stats["trained"] is False
