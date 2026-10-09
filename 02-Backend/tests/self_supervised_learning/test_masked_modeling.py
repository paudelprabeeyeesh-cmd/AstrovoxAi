import math
import random

import pytest

from self_supervised_learning.masked_modeling import (
    MaskedModelingConfig,
    mask_float_vector,
    mask_sequence,
    reconstruction_loss,
)


class TestMaskSequence:
    def test_returns_masked_and_indices(self):
        seq = ["a", "b", "c", "d", "e"]
        config = MaskedModelingConfig(mask_ratio=0.4)
        masked, indices = mask_sequence(seq, config)
        assert len(masked) == len(seq)
        assert len(indices) > 0

    def test_masked_positions_replaced(self):
        seq = ["a", "b", "c", "d", "e"]
        config = MaskedModelingConfig(mask_ratio=0.4, mask_token="<MASK>")
        masked, indices = mask_sequence(seq, config)
        for idx in indices:
            assert masked[idx] == "<MASK>"

    def test_default_config(self):
        seq = list(range(10))
        masked, indices = mask_sequence(seq)
        assert len(masked) == 10
        assert all(isinstance(i, int) for i in indices)

    def test_all_elements_can_be_masked(self):
        seq = ["a", "b"]
        config = MaskedModelingConfig(mask_ratio=1.0)
        masked, indices = mask_sequence(seq, config)
        assert len(indices) == 2


class TestMaskFloatVector:
    def test_returns_three_elements(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        masked, target, indices = mask_float_vector(x, mask_ratio=0.4)
        assert len(masked) == len(x)
        assert len(target) == len(x)
        assert isinstance(indices, list)

    def test_masked_positions_zeroed(self):
        x = [1.0, 2.0, 3.0, 4.0]
        masked, target, indices = mask_float_vector(x, mask_ratio=0.5)
        for idx in indices:
            assert masked[idx] == 0.0

    def test_target_preserves_original_values(self):
        x = [1.0, 2.0, 3.0, 4.0]
        masked, target, indices = mask_float_vector(x, mask_ratio=0.5)
        for idx in indices:
            assert target[idx] == pytest.approx(x[idx])

    def test_non_masked_preserved(self):
        x = [1.0, 2.0, 3.0, 4.0]
        masked, target, indices = mask_float_vector(x, mask_ratio=0.5)
        for idx in range(len(x)):
            if idx not in indices:
                assert masked[idx] == pytest.approx(x[idx])
                assert target[idx] == pytest.approx(0.0)


class TestReconstructionLoss:
    def test_perfect_reconstruction(self):
        original = [1.0, 2.0, 3.0]
        reconstructed = [1.0, 2.0, 3.0]
        mask_indices = [0, 2]
        loss = reconstruction_loss(original, reconstructed, mask_indices)
        assert loss == pytest.approx(0.0)

    def test_nonzero_reconstruction_error(self):
        original = [1.0, 2.0, 3.0]
        reconstructed = [1.0, 2.0, 3.0]
        mask_indices = [1]
        reconstructed[1] = 5.0
        loss = reconstruction_loss(original, reconstructed, mask_indices)
        assert loss > 0.0

    def test_empty_indices(self):
        loss = reconstruction_loss([1.0, 2.0], [1.0, 2.0], [])
        assert loss == pytest.approx(0.0)

    def test_returns_sqrt_mse(self):
        original = [0.0, 4.0]
        reconstructed = [0.0, 9.0]
        mask_indices = [1]
        loss = reconstruction_loss(original, reconstructed, mask_indices)
        expected = math.sqrt((4.0 - 9.0) ** 2)
        assert loss == pytest.approx(expected)
