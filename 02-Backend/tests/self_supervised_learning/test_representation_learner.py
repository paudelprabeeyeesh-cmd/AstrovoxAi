import random

import pytest

from self_supervised_learning.representation_learner import (
    RepresentationLearner,
    RepresentationLearnerConfig,
)


class TestRepresentationLearnerConfig:
    def test_default_values(self):
        config = RepresentationLearnerConfig()
        assert config.projection_dim == 128
        assert config.temperature == pytest.approx(0.1)
        assert config.mask_ratio == pytest.approx(0.3)

    def test_custom_values(self):
        config = RepresentationLearnerConfig(projection_dim=64, temperature=0.5, mask_ratio=0.2)
        assert config.projection_dim == 64
        assert config.temperature == pytest.approx(0.5)
        assert config.mask_ratio == pytest.approx(0.2)


class TestRepresentationLearner:
    def test_initialization(self):
        learner = RepresentationLearner()
        assert learner.config.projection_dim == 128
        assert learner.config.temperature == pytest.approx(0.1)
        assert learner.loss_history == []

    def test_encode_returns_projection_dim(self):
        learner = RepresentationLearner(RepresentationLearnerConfig(projection_dim=32))
        x = [1.0, 2.0, 3.0, 4.0]
        z = learner.encode(x)
        assert len(z) == 32

    def test_encode_same_input_same_output(self):
        learner = RepresentationLearner(RepresentationLearnerConfig(projection_dim=32))
        x = [1.0, 2.0, 3.0, 4.0]
        first = learner.encode(x)
        second = learner.encode(x)
        assert first == second

    def test_train_step_returns_contrastive_loss(self):
        learner = RepresentationLearner(RepresentationLearnerConfig(projection_dim=32))
        x = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        result = learner.train_step(x)
        assert "contrastive_loss" in result
        assert isinstance(result["contrastive_loss"], float)
        assert result["contrastive_loss"] >= 0.0

    def test_train_step_records_history(self):
        learner = RepresentationLearner(RepresentationLearnerConfig(projection_dim=32))
        x = [[1.0, 2.0, 3.0]]
        learner.train_step(x)
        assert len(learner.loss_history) == 1

    def test_masked_reconstruction_step(self):
        learner = RepresentationLearner(RepresentationLearnerConfig(projection_dim=32, mask_ratio=0.5))
        x = [[1.0, 2.0, 3.0, 4.0]]
        result = learner.masked_reconstruction_step(x)
        assert "reconstruction_loss" in result
        assert isinstance(result["reconstruction_loss"], float)

    def test_report(self):
        learner = RepresentationLearner()
        x = [[1.0, 2.0, 3.0]]
        learner.train_step(x)
        report = learner.report()
        assert report["num_steps"] == 1
        assert report["last_loss"] == pytest.approx(learner.loss_history[-1])
        assert report["config"]["temperature"] == pytest.approx(0.1)
        assert report["config"]["projection_dim"] == 128
        assert report["config"]["mask_ratio"] == pytest.approx(0.3)

    def test_report_no_steps(self):
        learner = RepresentationLearner()
        report = learner.report()
        assert report["num_steps"] == 0
        assert report["last_loss"] is None
