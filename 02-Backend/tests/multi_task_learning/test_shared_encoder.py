import math
import random

import pytest
from multi_task_learning.shared_encoder import SharedEncoder


class TestSharedEncoder:
    def test_forward_output_shape(self):
        encoder = SharedEncoder(input_dim=4, shared_dim=3)
        x = [0.5, -0.2, 1.0, -0.8]
        h = encoder.forward(x)
        assert len(h) == 3

    def test_forward_returns_non_negative(self):
        encoder = SharedEncoder(input_dim=2, shared_dim=4, seed=1)
        x = [1.0, -1.0]
        h = encoder.forward(x)
        for val in h:
            assert val >= 0.0

    def test_deterministic_with_seed(self):
        encoder1 = SharedEncoder(input_dim=3, shared_dim=2, seed=7)
        encoder2 = SharedEncoder(input_dim=3, shared_dim=2, seed=7)
        x = [0.1, 0.2, 0.3]
        assert encoder1.forward(x) == encoder2.forward(x)

    def test_different_seeds_different_weights(self):
        encoder1 = SharedEncoder(input_dim=2, shared_dim=2, seed=1)
        encoder2 = SharedEncoder(input_dim=2, shared_dim=2, seed=2)
        assert encoder1.get_parameters() != encoder2.get_parameters()

    def test_get_parameters_returns_list_of_lists(self):
        encoder = SharedEncoder(input_dim=3, shared_dim=2)
        params = encoder.get_parameters()
        assert isinstance(params, list)
        assert len(params) == 3
        for row in params:
            assert isinstance(row, list)
            assert len(row) == 2

    def test_forward_correctness(self):
        encoder = SharedEncoder(input_dim=2, shared_dim=2, seed=0)
        x = [1.0, 0.0]
        h = encoder.forward(x)
        for val in h:
            assert isinstance(val, float)

    def test_reproducibility_forward(self):
        encoder = SharedEncoder(input_dim=2, shared_dim=2, seed=42)
        x = [0.1, 0.2]
        first = encoder.forward(x)
        second = encoder.forward(x)
        assert first == second

    def test_zero_input(self):
        encoder = SharedEncoder(input_dim=2, shared_dim=3, seed=0)
        x = [0.0, 0.0]
        h = encoder.forward(x)
        assert len(h) == 3
        for val in h:
            assert val >= 0.0

    def test_negative_input(self):
        encoder = SharedEncoder(input_dim=2, shared_dim=3, seed=0)
        x = [-1.0, -2.0]
        h = encoder.forward(x)
        assert len(h) == 3
        for val in h:
            assert val >= 0.0

    def test_default_seed(self):
        encoder = SharedEncoder(input_dim=2, shared_dim=2)
        assert encoder.seed == 42
