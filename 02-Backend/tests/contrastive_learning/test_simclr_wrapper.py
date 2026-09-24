import numpy as np
import pytest
from contrastive_learning.simclr_wrapper import SimCLRWrapper
from contrastive_learning.projection_head import ProjectionHead
from contrastive_learning.temperature_scheduler import TemperatureScheduler
from contrastive_learning.triplet_miner import TripletMiner


class TestSimCLRWrapper:
    def test_initialization(self):
        model = SimCLRWrapper(input_dim=32, projection_dim=64, hidden_dim=128, temperature=0.07)
        assert model.input_dim == 32
        assert model.projection_dim == 64
        assert model.hidden_dim == 128
        assert model.temperature_scheduler.get() == pytest.approx(0.07)
        assert len(model.loss_history) == 0

    def test_train_step_basic(self):
        model = SimCLRWrapper(input_dim=32, projection_dim=64, hidden_dim=128, seed=42)
        x_i = np.random.randn(8, 32).astype(np.float64)
        x_j = np.random.randn(8, 32).astype(np.float64)
        result = model.train_step(x_i, x_j)
        assert "loss" in result
        assert "temperature" in result
        assert isinstance(result["loss"], float)
        assert result["loss"] >= 0.0
        assert len(model.loss_history) == 1

    def test_train_step_dimension_mismatch(self):
        model = SimCLRWrapper(input_dim=32)
        x_i = np.random.randn(8, 16).astype(np.float64)
        x_j = np.random.randn(8, 32).astype(np.float64)
        with pytest.raises(ValueError, match="Input dimensions do not match"):
            model.train_step(x_i, x_j)

    def test_train_step_with_labels(self):
        model = SimCLRWrapper(input_dim=32, projection_dim=64, hidden_dim=128, seed=42)
        x_i = np.random.randn(8, 32).astype(np.float64)
        x_j = np.random.randn(8, 32).astype(np.float64)
        labels = np.array([0, 0, 1, 1, 2, 2, 3, 3])
        result = model.train_step(x_i, x_j, labels=labels)
        assert "loss" in result
        assert "triplet_loss" in result
        assert result["triplet_loss"] >= 0.0

    def test_encode(self):
        model = SimCLRWrapper(input_dim=32, projection_dim=64, hidden_dim=128, seed=42)
        x = np.random.randn(8, 32).astype(np.float64)
        z = model.encode(x)
        assert z.shape == (8, 64)

    def test_encode_dimension_mismatch(self):
        model = SimCLRWrapper(input_dim=32)
        x = np.random.randn(8, 16).astype(np.float64)
        with pytest.raises(ValueError, match="Input dimensions do not match"):
            model.encode(x)

    def test_evaluate(self):
        model = SimCLRWrapper(input_dim=32, projection_dim=64, hidden_dim=128, seed=42)
        x = np.random.randn(8, 32).astype(np.float64)
        x_pos = np.random.randn(8, 32).astype(np.float64)
        x_neg = np.random.randn(8, 32).astype(np.float64)
        result = model.evaluate(x, x_pos, x_neg)
        assert "triplet_loss" in result
        assert result["triplet_loss"] >= 0.0

    def test_get_report_empty(self):
        model = SimCLRWrapper(input_dim=16)
        report = model.get_report()
        assert "num_steps" in report
        assert report["num_steps"] == 0
        assert report["last_loss"] is None
        assert report["temperature"] == pytest.approx(0.07)

    def test_get_report_after_training(self):
        model = SimCLRWrapper(input_dim=16, seed=42)
        x_i = np.random.randn(4, 16).astype(np.float64)
        x_j = np.random.randn(4, 16).astype(np.float64)
        model.train_step(x_i, x_j)
        report = model.get_report()
        assert report["num_steps"] == 1
        assert report["last_loss"] >= 0.0
        assert report["mean_loss"] == pytest.approx(report["last_loss"])

    def test_report_mean_loss_after_multiple_steps(self):
        model = SimCLRWrapper(input_dim=16, seed=42)
        x_i = np.random.randn(4, 16).astype(np.float64)
        x_j = np.random.randn(4, 16).astype(np.float64)
        for _ in range(15):
            model.train_step(x_i, x_j)
        report = model.get_report()
        assert report["num_steps"] == 15
        assert report["mean_loss"] >= 0.0

    def test_loss_non_negative(self):
        model = SimCLRWrapper(input_dim=32, projection_dim=64, hidden_dim=128, seed=42)
        for _ in range(5):
            x_i = np.random.randn(8, 32).astype(np.float64)
            x_j = np.random.randn(8, 32).astype(np.float64)
            result = model.train_step(x_i, x_j)
            assert result["loss"] >= 0.0

    def test_projections_output_shape(self):
        model = SimCLRWrapper(input_dim=32, projection_dim=64, hidden_dim=128, seed=42)
        x_i = np.random.randn(8, 32).astype(np.float64)
        z_i = model.projection_head.forward(x_i)
        assert z_i.shape == (8, 64)

    def test_normalize_unit_norms(self):
        model = SimCLRWrapper(input_dim=16)
        x = np.random.randn(8, 16).astype(np.float64)
        z = model._normalize(x)
        norms = np.linalg.norm(z, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-12)

    def test_nt_xent_loss_identical_inputs(self):
        model = SimCLRWrapper(input_dim=16, projection_dim=64, hidden_dim=128, seed=42)
        x = np.random.randn(8, 16).astype(np.float64)
        z = model.projection_head.forward(x)
        loss = model._nt_xent_loss(z, z)
        assert loss == pytest.approx(0.0, abs=1e-12)
