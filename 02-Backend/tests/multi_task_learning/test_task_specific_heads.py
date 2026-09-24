import math
import random

import pytest
from multi_task_learning.task_specific_heads import TaskSpecificHead


class TestTaskSpecificHead:
    def test_forward_output_shape(self):
        head = TaskSpecificHead(shared_dim=4, output_dim=2)
        h = [0.1, 0.2, 0.3, 0.4]
        out = head.forward(h)
        assert len(out) == 2

    def test_forward_returns_floats(self):
        head = TaskSpecificHead(shared_dim=3, output_dim=1, seed=0)
        h = [0.5, -0.2, 1.0]
        out = head.forward(h)
        assert isinstance(out[0], float)

    def test_deterministic_with_seed(self):
        head1 = TaskSpecificHead(shared_dim=3, output_dim=2, seed=5)
        head2 = TaskSpecificHead(shared_dim=3, output_dim=2, seed=5)
        h = [0.1, 0.2, 0.3]
        assert head1.forward(h) == head2.forward(h)

    def test_different_seeds_different_outputs(self):
        head1 = TaskSpecificHead(shared_dim=2, output_dim=2, seed=1)
        head2 = TaskSpecificHead(shared_dim=2, output_dim=2, seed=2)
        h = [0.5, 0.5]
        out1 = head1.forward(h)
        out2 = head2.forward(h)
        assert out1 != out2

    def test_get_parameters_structure(self):
        head = TaskSpecificHead(shared_dim=3, output_dim=2)
        params = head.get_parameters()
        assert "weights" in params
        assert "bias" in params
        assert len(params["weights"]) == 3
        assert len(params["bias"]) == 2

    def test_get_parameters_returns_copies(self):
        head = TaskSpecificHead(shared_dim=2, output_dim=2, seed=0)
        params = head.get_parameters()
        params["weights"][0][0] = 999.0
        assert head.weights[0][0] != 999.0

    def test_output_dimension(self):
        head = TaskSpecificHead(shared_dim=5, output_dim=3)
        h = [0.1, 0.2, 0.3, 0.4, 0.5]
        out = head.forward(h)
        assert len(out) == 3
