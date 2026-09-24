import numpy as np
import pytest
from advanced_learning.curriculum_learning_advanced import AdvancedCurriculumLearner, CurriculumConfig


class TestAdvancedCurriculumLearner:
    def test_initialization(self):
        config = CurriculumConfig(input_dim=32, output_dim=4)
        cl = AdvancedCurriculumLearner(config)
        assert cl.config.input_dim == 32
        assert cl.config.pacing_type == "linear"
        assert cl.config.pacing_start_frac == 0.1
        assert len(cl.loss_history) == 0

    def test_score_difficulty_loss(self):
        config = CurriculumConfig(input_dim=32, output_dim=4, difficulty_metric="loss")
        cl = AdvancedCurriculumLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        scores = cl.score_difficulty(x, y)
        assert scores.shape == (16,)
        assert len(cl.difficulty_scores) == 16

    def test_score_difficulty_gradient(self):
        config = CurriculumConfig(input_dim=32, output_dim=4, difficulty_metric="gradient_norm")
        cl = AdvancedCurriculumLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        scores = cl.score_difficulty(x, y)
        assert scores.shape == (16,)

    def test_update_mask(self):
        config = CurriculumConfig(input_dim=32, output_dim=4, pacing_epochs=5)
        cl = AdvancedCurriculumLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        np.random.randn(16, 4).astype(np.float64)
        mask = cl.update_mask(x, epoch=0)
        assert mask.shape == (16,)
        assert isinstance(mask, np.ndarray)
        assert mask.dtype == bool

    def test_train_step(self):
        config = CurriculumConfig(input_dim=32, output_dim=4, pacing_epochs=5)
        cl = AdvancedCurriculumLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        result = cl.train_step(x, y, epoch=3)
        assert "loss" in result
        assert "epoch" in result
        assert result["epoch"] == 3
        assert "samples_used" in result
        assert len(cl.loss_history) == 1

    def test_pacing_linear(self):
        config = CurriculumConfig(input_dim=32, output_dim=4, pacing_type="linear", pacing_start_frac=0.0, pacing_epochs=10)
        cl = AdvancedCurriculumLearner(config)
        assert cl._compute_pacing(0) == pytest.approx(0.0)
        assert cl._compute_pacing(10) == pytest.approx(1.0)

    def test_pacing_exponential(self):
        config = CurriculumConfig(input_dim=32, output_dim=4, pacing_type="exponential", pacing_start_frac=0.5, pacing_epochs=10)
        cl = AdvancedCurriculumLearner(config)
        frac = cl._compute_pacing(0)
        assert frac >= 0.0

    def test_get_curriculum_report(self):
        config = CurriculumConfig(input_dim=32, output_dim=4)
        cl = AdvancedCurriculumLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        cl.train_step(x, y, epoch=1)
        report = cl.get_curriculum_report()
        assert "num_steps" in report
        assert report["pacing_type"] == "linear"
        assert "difficulty_metric" in report
