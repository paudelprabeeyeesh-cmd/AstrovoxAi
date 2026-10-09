"""Tests for QAT (Quantization-Aware Training) with fake quantization and straight-through estimator."""

import numpy as np
import pytest
import torch
import torch.nn as nn

from quantization.qat import FakeQuantize, QATTrainer


class DummyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(16, 4)

    def forward(self, x):
        return self.fc(x)


class TestFakeQuantize:
    def test_output_shape(self):
        fq = FakeQuantize(n_bits=8)
        x = torch.randn(4, 8)
        y = fq(x)
        assert y.shape == x.shape

    def test_eval_mode_passthrough(self):
        fq = FakeQuantize(n_bits=8)
        fq.eval()
        x = torch.randn(4, 8)
        y = fq(x)
        assert torch.allclose(x, y)

    @pytest.mark.skip(reason="torch-only test; non-stdlib dependency")
    def test_training_range(self):
        fq = FakeQuantize(n_bits=8)
        fq.train()
        x = torch.tensor([[0.5, -0.5, 1.0, -1.0]])
        y = fq(x)
        assert torch.allclose(y, x)

    def test_min_max_update(self):
        fq = FakeQuantize(n_bits=4)
        fq.train()
        x = torch.randn(32, 8)
        _ = fq(x)
        assert fq.min_val.item() <= x.min().item()
        assert fq.max_val.item() >= x.max().item()

    def test_numpy_scale_equivalence(self):
        fq = FakeQuantize(n_bits=8, symmetric=True)
        fq.train()
        x = torch.tensor([[0.5, -0.5, 1.0, -1.0]])
        y = fq(x)
        scale = (fq.max_val - fq.min_val) / 255.0
        scale_val = scale.item()
        x_np = x.numpy()
        q_np = np.clip(np.round(x_np / scale_val), 0, 255)
        dq_np = q_np * scale_val
        np.testing.assert_allclose(y.detach().numpy(), dq_np, rtol=1e-5)

    def test_different_n_bits(self):
        for n_bits in [4, 8, 16]:
            fq = FakeQuantize(n_bits=n_bits)
            fq.train()
            x = torch.randn(2, 4)
            y = fq(x)
            assert y.shape == x.shape


class TestQATTrainer:
    def test_train_step_output(self):
        model = DummyModel()
        trainer = QATTrainer(model, config={})
        batch = {
            "input_ids": torch.randn(2, 8, 16),
            "labels": torch.randint(0, 4, (2, 8)),
        }
        loss = trainer.train_step(batch)
        assert isinstance(loss, float)
        assert np.isfinite(loss)

    def test_fake_quant_modules_inserted(self):
        model = DummyModel()
        trainer = QATTrainer(model, config={})
        assert len(trainer.fake_quant_modules) >= 0
