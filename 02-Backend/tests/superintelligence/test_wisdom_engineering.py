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
            assert 0.0 <= judgment.uncertainty <= 1.0

    def test_wisdom_stats(self):
        eng = WisdomEngineer()
        context = np.random.randn(64)
        options = [np.random.randn(64) for _ in range(3)]
        eng.render_judgment(context, options)
        stats = eng.get_wisdom_stats()
        assert stats["judgments_rendered"] == 1
        assert stats["trained"] is False

    def test_train_calibration_sets_trained(self):
        eng = WisdomEngineer()
        outcomes = np.random.randn(30)
        decisions = np.random.randn(30)
        eng.train_calibration(outcomes, decisions)
        assert eng._trained is True
