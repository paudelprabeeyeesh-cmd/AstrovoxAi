import numpy as np
import pytest
from tensor_engine.autograd import Tensor


def assert_allclose(a, b, atol=1e-6):
    np.testing.assert_allclose(a, b, atol=atol)


class TestAutograd:
    def test_add(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        b = Tensor(np.array([[5.0, 6.0], [7.0, 8.0]]), requires_grad=True)
        c = a + b
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, np.ones_like(a.data))
        assert_allclose(b.grad, np.ones_like(b.data))

    def test_add_broadcast(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        b = Tensor(np.array([10.0, 20.0]), requires_grad=True)
        c = a + b
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, np.ones_like(a.data))
        assert_allclose(b.grad, np.array([2.0, 2.0]))

    def test_mul(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        b = Tensor(np.array([[5.0, 6.0], [7.0, 8.0]]), requires_grad=True)
        c = a * b
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, b.data)
        assert_allclose(b.grad, a.data)

    def test_matmul(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        b = Tensor(np.array([[5.0, 6.0], [7.0, 8.0]]), requires_grad=True)
        c = a @ b
        c.backward(np.ones_like(c.data))
        expected_grad_a = np.matmul(np.ones_like(c.data), b.data.T)
        expected_grad_b = np.matmul(a.data.T, np.ones_like(c.data))
        assert_allclose(a.grad, expected_grad_a)
        assert_allclose(b.grad, expected_grad_b)

    def test_pow(self):
        a = Tensor(np.array([1.0, 2.0, 3.0]), requires_grad=True)
        b = Tensor(np.array([2.0, 2.0, 2.0]), requires_grad=False)
        c = a ** b
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, 2 * np.array([1.0, 2.0, 3.0]))

    def test_exp(self):
        a = Tensor(np.array([0.0, 1.0, 2.0]), requires_grad=True)
        c = a.exp()
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, np.exp(a.data))

    def test_log(self):
        a = Tensor(np.array([1.0, 2.0, 3.0]), requires_grad=True)
        c = a.log()
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, 1.0 / np.array([1.0, 2.0, 3.0]))

    def test_sum(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        c = a.sum()
        c.backward()
        assert_allclose(a.grad, np.ones_like(a.data))

    def test_sum_dim(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        c = a.sum(dim=0)
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, np.ones_like(a.data))

    def test_mean(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        c = a.mean()
        c.backward()
        assert_allclose(a.grad, np.ones_like(a.data) / a.data.size)

    def test_max(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        c = a.max(dim=0)
        c.backward(np.ones_like(c.data))
        expected = np.zeros_like(a.data)
        expected[1, :] = 1.0
        assert_allclose(a.grad, expected)

    def test_relu(self):
        a = Tensor(np.array([-1.0, 0.0, 1.0, 2.0]), requires_grad=True)
        c = a.relu()
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, np.array([0.0, 0.0, 1.0, 1.0]))

    def test_sigmoid(self):
        a = Tensor(np.array([0.0, 1.0, -1.0]), requires_grad=True)
        c = a.sigmoid()
        c.backward(np.ones_like(c.data))
        s = 1.0 / (1.0 + np.exp(-a.data))
        assert_allclose(a.grad, s * (1 - s))

    def test_tanh(self):
        a = Tensor(np.array([0.0, 1.0, -1.0]), requires_grad=True)
        c = a.tanh()
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, 1 - np.tanh(a.data) ** 2)

    def test_gelu(self):
        a = Tensor(np.array([0.0, 1.0, -1.0]), requires_grad=True)
        c = a.gelu()
        c.backward(np.ones_like(c.data))
        # Just check it runs and has valid gradient
        assert a.grad is not None
        assert np.all(np.isfinite(a.grad))

    def test_swish(self):
        a = Tensor(np.array([0.0, 1.0, -1.0]), requires_grad=True)
        c = a.swish()
        c.backward(np.ones_like(c.data))
        assert a.grad is not None
        assert np.all(np.isfinite(a.grad))

    def test_softmax(self):
        a = Tensor(np.array([[0.0, 1.0, 2.0], [2.0, 1.0, 0.0]]), requires_grad=True)
        c = a.softmax(dim=-1)
        c.backward(np.ones_like(c.data))
        assert a.grad is not None
        assert np.all(np.isfinite(a.grad))

    def test_layer_norm(self):
        a = Tensor(np.random.randn(4, 8), requires_grad=True)
        c = a.layer_norm([8])
        c.backward(np.ones_like(c.data))
        assert a.grad is not None
        assert np.all(np.isfinite(a.grad))

    def test_rms_norm(self):
        a = Tensor(np.random.randn(4, 8), requires_grad=True)
        c = a.rms_norm([8])
        c.backward(np.ones_like(c.data))
        assert a.grad is not None
        assert np.all(np.isfinite(a.grad))

    def test_chain_rule_add_mul(self):
        a = Tensor(np.array([[1.0, 2.0]]), requires_grad=True)
        b = Tensor(np.array([[3.0, 4.0]]), requires_grad=True)
        c = a + b
        d = c * Tensor(np.array([[2.0, 2.0]]))
        d.backward(np.ones_like(d.data))
        assert_allclose(a.grad, np.array([[2.0, 2.0]]))
        assert_allclose(b.grad, np.array([[2.0, 2.0]]))

    def test_chain_rule_matmul_add(self):
        a = Tensor(np.array([[1.0, 2.0]]), requires_grad=True)
        b = Tensor(np.array([[3.0], [4.0]]), requires_grad=True)
        c = a @ b
        d = c + Tensor(np.array([[1.0]]))
        d.backward()
        assert_allclose(a.grad, np.array([[3.0, 4.0]]))
        assert_allclose(b.grad, np.array([[1.0], [2.0]]))

    def test_backward_topological_sort(self):
        x = Tensor(np.array([1.0, 2.0]), requires_grad=True)
        y = x * 2
        z = y + 1
        z.backward(np.ones_like(z.data))
        assert_allclose(x.grad, np.array([2.0, 2.0]))

    def test_no_grad(self):
        a = Tensor(np.array([1.0, 2.0]), requires_grad=False)
        b = Tensor(np.array([3.0, 4.0]), requires_grad=True)
        c = a + b
        assert c.requires_grad is True
        c.backward(np.ones_like(c.data))
        assert a.grad is None

    def test_zero_grad(self):
        a = Tensor(np.array([1.0, 2.0]), requires_grad=True)
        c = a * 2
        c.backward()
        assert_allclose(a.grad, np.array([2.0, 2.0]))
        a.zero_grad()
        assert_allclose(a.grad, np.zeros_like(a.data))

    def test_reshape_backward(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        b = a.reshape(4)
        c = b.sum()
        c.backward()
        assert a.grad.shape == (2, 2)

    def test_transpose_backward(self):
        a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
        b = a.transpose(0, 1)
        c = (b * b).sum()
        c.backward()
        assert_allclose(a.grad, 2 * a.data)

    def test_neg_backward(self):
        a = Tensor(np.array([1.0, -2.0, 3.0]), requires_grad=True)
        c = -a
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, np.array([-1.0, -1.0, -1.0]))

    def test_sub_backward(self):
        a = Tensor(np.array([1.0, 2.0]), requires_grad=True)
        b = Tensor(np.array([3.0, 4.0]), requires_grad=True)
        c = a - b
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, np.ones_like(a.data))
        assert_allclose(b.grad, -np.ones_like(b.data))

    def test_truediv_backward(self):
        a = Tensor(np.array([4.0, 9.0]), requires_grad=True)
        b = Tensor(np.array([2.0, 3.0]), requires_grad=False)
        c = a / b
        c.backward(np.ones_like(c.data))
        assert_allclose(a.grad, 1.0 / np.array([2.0, 3.0]))
