"""Tests for mixed precision and loss scaling."""

import numpy as np
import pytest

from astrovox import tensor
from astrovox.mixed_precision import (
    GradScaler,
    MixedPrecisionTrainer,
    PrecisionConfig,
    autocast,
    contains_dtype,
    from_low_precision,
    has_non_finite,
    to_low_precision,
)
from astrovox.nn import Linear, ReLU, Sequential
from astrovox.ops import cross_entropy
from astrovox.optim import AdamW


class TestGradScaler:
    def test_scale_loss_multiplies(self):
        scaler = GradScaler(scale=1024.0)
        scaled = scaler.scale_loss(tensor([1.0, 2.0]))
        assert np.allclose(scaled.numpy(), np.array([1024.0, 2048.0], dtype=np.float32))

    def test_disabled_scaler_is_a_passthrough(self):
        scaler = GradScaler(scale=1024.0, enabled=False)
        assert np.allclose(scaler.scale_loss(tensor([1.0])).numpy(), np.array([1.0], dtype=np.float32))

    def test_unscale_divides_in_place(self):
        grad = tensor([10.0, 20.0])
        grad._grad = tensor([100.0, 200.0])
        scaler = GradScaler(scale=100.0)
        norm = scaler.unscale([grad._grad])
        assert np.allclose(grad._grad.numpy(), np.array([1.0, 2.0], dtype=np.float32))
        assert norm == pytest.approx(np.sqrt(5.0), rel=1e-5)

    def test_overflow_skips_the_step_and_halves_the_scale(self):
        scaler = GradScaler(scale=1024.0)
        assert scaler.step_update(True) is True
        assert scaler.scale == 512.0

    def test_clean_step_advances_the_growth_tracker(self):
        scaler = GradScaler(scale=1024.0, growth_interval=3)
        assert [scaler.step_update(False) for _ in range(3)] == [False, False, False]
        assert scaler.scale == 2048.0

    def test_scale_never_drops_below_one(self):
        scaler = GradScaler(scale=1.0)
        for _ in range(20):
            scaler.step_update(True)
        assert scaler.scale >= 1.0

    def test_scale_is_capped(self):
        scaler = GradScaler(scale=1.0, growth_interval=1, max_scale=8.0)
        for _ in range(20):
            scaler.step_update(False)
        assert scaler.scale <= 8.0

    def test_overflow_resets_the_growth_tracker(self):
        scaler = GradScaler(scale=1024.0, growth_interval=5)
        scaler.step_update(False)
        scaler.step_update(True)
        assert scaler.growth_tracker == 0

    def test_state_round_trip(self):
        scaler = GradScaler(scale=2048.0)
        scaler.step_update(True)
        data = scaler.state_dict()
        restored = GradScaler()
        restored.load_state_dict(data)
        assert restored.scale == scaler.scale
        assert restored.growth_tracker == scaler.growth_tracker

    def test_rejects_a_non_positive_scale(self):
        with pytest.raises(ValueError, match="must be positive"):
            GradScaler(scale=0.0)

    def test_rejects_a_bad_backoff(self):
        with pytest.raises(ValueError, match="backoff_factor"):
            GradScaler(backoff_factor=1.5)


class TestNonFiniteDetection:
    def test_detects_nan(self):
        assert has_non_finite([tensor([np.nan, 1.0], dtype="float32")]) is True

    def test_detects_infinity(self):
        assert has_non_finite([tensor([np.inf], dtype="float32")]) is True

    def test_accepts_finite(self):
        assert has_non_finite([tensor([1.0, 2.0])]) is False

    def test_none_entries_are_skipped(self):
        assert has_non_finite([None, tensor([1.0])]) is False
        assert has_non_finite([None, tensor([np.nan])]) is True


class TestLowPrecisionConversion:
    def test_float16_round_trip_preserves_most_bits(self):
        original = tensor(np.array([1.5, -2.25, 0.125], dtype=np.float32))
        restored = from_low_precision(to_low_precision(original))
        assert np.allclose(restored.numpy(), original.numpy(), atol=1e-2)

    def test_conversion_halves_the_bytes(self):
        original = tensor(np.zeros((64, 64), dtype=np.float32))
        assert to_low_precision(original).nbytes == original.nbytes // 2

    def test_dtype_preserved(self):
        reduced = to_low_precision(tensor(np.zeros(4, dtype=np.float32)))
        assert reduced.dtype.name == "float16"

    def test_identifies_reduced_precision_types(self):
        assert contains_dtype("float16") is True
        assert contains_dtype("float32") is False


class TestAutocast:
    def test_usable_as_context_manager(self):
        with autocast("float16"):
            pass

    def test_usable_as_decorator(self):
        @autocast("float16")
        def compute():
            return tensor([1.0])

        assert compute().item() == 1.0

    def test_preserves_the_reduction_list(self):
        assert "cross_entropy" in autocast._preserved
        assert "mean" in autocast._preserved


class TestMixedPrecisionTraining:
    def _setup(self, seed: int = 0):
        rng = np.random.default_rng(seed)
        model = Sequential(Linear(4, 8), ReLU(), Linear(8, 2))
        # Pinned so two setups differ only in the loss scale under test.
        for _, p in model.named_parameters():
            p.numpy()[...] = (rng.standard_normal(p.shape.dims) * 0.3).astype(np.float32)
        x = tensor(rng.standard_normal((32, 4)).astype(np.float32))
        y = tensor(rng.integers(0, 2, 32).astype(np.int64))
        return model, x, y, AdamW(list(model.parameters()), lr=0.01)

    def test_a_step_reports_its_outcome(self):
        model, x, y, optimizer = self._setup()
        trainer = MixedPrecisionTrainer(model, optimizer, PrecisionConfig(loss_scale=1024.0))
        record = trainer.step(lambda: cross_entropy(model(x), y))
        assert "loss" in record
        assert record["skipped"] is False
        assert record["scale"] == 1024.0
        assert record["grad_norm"] > 0
        assert any(p.grad is not None for p in model.parameters())

    def test_step_updates_parameters(self):
        model, x, y, optimizer = self._setup()
        before = model.state_dict()
        trainer = MixedPrecisionTrainer(model, optimizer, PrecisionConfig())
        trainer.step(lambda: cross_entropy(model(x), y))
        after = model.state_dict()
        assert any(
            not np.array_equal(before[name].numpy(), after[name].numpy()) for name in before
        )

    def test_loss_scaling_does_not_change_the_update(self):
        """The scale must be numerically invisible once unscaled."""
        results = []
        for scale in (1.0, 1024.0, 65536.0):
            model, x, y, optimizer = self._setup()
            trainer = MixedPrecisionTrainer(model, optimizer, PrecisionConfig(loss_scale=scale))
            trainer.step(lambda: cross_entropy(model(x), y))
            results.append(
                np.concatenate([p.numpy().ravel() for _, p in model.named_parameters()])
            )
        assert np.allclose(results[0], results[1], atol=1e-4)
        assert np.allclose(results[0], results[2], atol=1e-4)

    def test_overflow_skips_the_update_and_reduces_the_scale(self):
        model, x, y, optimizer = self._setup()
        trainer = MixedPrecisionTrainer(model, optimizer, PrecisionConfig(loss_scale=1024.0))
        before = model.state_dict()

        # The loss has to be a real graph node, and large enough that scaling
        # it by 1024 overflows float32.
        def exploding_loss():
            return model(x).sum() * 1.0e38

        record = trainer.step(exploding_loss)
        assert record["skipped"] is True
        assert record["scale"] == 512.0
        after = model.state_dict()
        for name in before:
            assert np.array_equal(before[name].numpy(), after[name].numpy(), equal_nan=True)

    def test_scale_recovers_after_an_overflow(self):
        model, x, y, optimizer = self._setup()
        trainer = MixedPrecisionTrainer(model, optimizer, PrecisionConfig(loss_scale=1024.0))
        trainer.scaler.growth_interval = 2
        trainer.step(lambda: model(x).sum() * 1.0e38)
        assert trainer.scaler.scale == 512.0
        for _ in range(2):
            trainer.step(lambda: cross_entropy(model(x), y))
        assert trainer.scaler.scale == 1024.0
        assert trainer.skipped_steps == 1

    def test_training_converges_with_scaling(self):
        rng = np.random.default_rng(1)
        model = Sequential(Linear(4, 16), ReLU(), Linear(16, 2))
        data = rng.standard_normal((128, 4)).astype(np.float32)
        labels = (data @ rng.standard_normal(4) > 0).astype(np.int64)
        x = tensor(data)
        y = tensor(labels)
        optimizer = AdamW(list(model.parameters()), lr=0.02)
        trainer = MixedPrecisionTrainer(model, optimizer, PrecisionConfig(loss_scale=1024.0))

        first = last = None
        for step in range(80):
            record = trainer.step(lambda: cross_entropy(model(x), y))
            if step == 0:
                first = record["loss"]
            last = record["loss"]
        assert last < first, f"{first} -> {last}"

    def test_state_round_trip(self):
        model, x, y, optimizer = self._setup()
        trainer = MixedPrecisionTrainer(model, optimizer, PrecisionConfig(loss_scale=2048.0))
        trainer.step(lambda: cross_entropy(model(x), y))
        data = trainer.state_dict()
        restored = MixedPrecisionTrainer(model, optimizer)
        restored.load_state_dict(data)
        assert restored.scaler.scale == trainer.scaler.scale
        assert restored.total_steps == trainer.total_steps


class TestPrecisionConfig:
    def test_defaults_to_float16(self):
        config = PrecisionConfig()
        assert config.compute_dtype.name == "float16"
        assert config.loss_scale > 0

    def test_serializes(self):
        assert PrecisionConfig().to_dict()["compute_dtype"] == "float16"