import numpy as np
import pytest
from contrastive_learning.projection_head import ProjectionHead


class TestProjectionHead:
    def test_initialization(self):
        head = ProjectionHead(input_dim=32, hidden_dim=64, output_dim=16)
        assert head.input_dim == 32
        assert head.hidden_dim == 64
        assert head.output_dim == 16
        assert head.W1.shape == (32, 64)
        assert head.W2.shape == (64, 16)

    def test_forward_shape(self):
        head = ProjectionHead(input_dim=32, hidden_dim=64, output_dim=16)
        x = np.random.randn(8, 32).astype(np.float64)
        z = head.forward(x)
        assert z.shape == (8, 16)

    def test_call_forward(self):
        head = ProjectionHead(input_dim=16, hidden_dim=32, output_dim=8)
        x = np.random.randn(4, 16).astype(np.float64)
        z = head(x)
        assert z.shape == (4, 8)

    def test_deterministic_with_seed(self):
        head1 = ProjectionHead(input_dim=8, seed=42)
        head2 = ProjectionHead(input_dim=8, seed=42)
        x = np.random.randn(4, 8).astype(np.float64)
        assert np.allclose(head1(x), head2(x))

    def test_relu_activation(self):
        head = ProjectionHead(input_dim=4, hidden_dim=8, output_dim=4)
        x = np.array([[-1.0, 0.0, 1.0, 2.0]], dtype=np.float64)
        hidden = head._relu(x @ head.W1 + head.b1)
        assert np.all(hidden >= -1e-9)

    def test_output_dim(self):
        head = ProjectionHead(input_dim=10, hidden_dim=20, output_dim=5)
        x = np.random.randn(3, 10).astype(np.float64)
        z = head.forward(x)
        assert z.shape[1] == 5

    def test_params_attribute(self):
        head = ProjectionHead(input_dim=8, hidden_dim=16, output_dim=4)
        assert len(head.params) == 4
        assert head.W1.shape == (8, 16)
        assert head.b1.shape == (16,)
        assert head.W2.shape == (16, 4)
        assert head.b2.shape == (4,)
