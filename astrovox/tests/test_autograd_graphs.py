"""Tiny hand-built graphs, verified against analytic gradients.

These are the smallest cases that isolate one engine behaviour at a time:
shape alignment, broadcast reduction, multi-parent accumulation, and view
inversion. Each expected value is derived by hand rather than numerically, so
a mistake in the engine cannot hide behind a matching mistake in the reference.
"""

import numpy as np
import pytest

from astrovox import tensor
from astrovox.autograd import backward, check_gradients, no_grad
from astrovox.ops import add, cross_entropy, exp, log, matmul, mean, mul, neg, sqrt, sub, sum as sum_op
from astrovox.tensor.tensor import Tensor


class TestSingleOpGraphs:
    """One operation, so a failure points at exactly one backward."""

    def test_neg_gradient_is_minus_one(self):
        t = tensor([1.0, 2.0, 3.0]).requires_grad_(True)
        backward(neg(t).sum())
        assert np.array_equal(t.grad.numpy(), np.full(3, -1.0, dtype=np.float32))

    def test_exp_gradient_is_its_own_output(self):
        values = np.array([0.5, -1.0, 2.0], dtype=np.float32)
        t = tensor(values).requires_grad_(True)
        backward(exp(t).sum())
        assert np.allclose(t.grad.numpy(), np.exp(values), atol=1e-6)

    def test_sqrt_gradient_is_half_over_sqrt(self):
        values = np.array([1.0, 4.0, 9.0], dtype=np.float32)
        t = tensor(values).requires_grad_(True)
        backward(sqrt(t).sum())
        assert np.allclose(t.grad.numpy(), 0.5 / np.sqrt(values), atol=1e-6)

    def test_log_gradient_is_reciprocal(self):
        values = np.array([0.5, 1.0, 2.0], dtype=np.float32)
        t = tensor(values).requires_grad_(True)
        backward(log(t).sum())
        assert np.allclose(t.grad.numpy(), 1.0 / values, atol=1e-6)

    def test_single_return_is_wrapped_as_a_tuple(self):
        """A one-input backward returning a bare tensor must not be iterated.

        Returning a tensor instead of a tuple would make the engine walk that
        tensor's rows and treat each as a separate input gradient.
        """
        t = tensor([[1.0, 2.0], [3.0, 4.0]]).requires_grad_(True)
        backward(sqrt(t).sum())
        assert t.grad.shape == t.shape
        assert np.allclose(t.grad.numpy(), 0.5 / np.sqrt(t.numpy()), atol=1e-6)


class TestBroadcastReduction:
    """A gradient broad into an operand has to be summed back down."""

    def test_broadcast_add_sums_over_broadcast_axis(self):
        matrix = tensor([[1.0, 2.0], [3.0, 4.0]]).requires_grad_(True)
        vector = tensor([10.0, 20.0])
        # Each matrix element appears once, so the gradient is all ones.
        backward(add(matrix, vector).sum())
        assert np.array_equal(matrix.grad.numpy(), np.ones((2, 2), dtype=np.float32))

    def test_broadcast_mul_scales_by_the_other_operand(self):
        matrix = tensor([[1.0, 2.0], [3.0, 4.0]]).requires_grad_(True)
        vector = tensor([10.0, 20.0])
        backward(mul(matrix, vector).sum())
        assert np.allclose(matrix.grad.numpy(), np.broadcast_to(np.array([10.0, 20.0]), (2, 2)), atol=1e-6)

    def test_column_broadcast_reduces_over_batch(self):
        """A shape-``(n, 1)`` operand receives a sum over the batch axis."""
        column = tensor([[1.0], [2.0]]).requires_grad_(True)
        row = tensor([10.0, 20.0, 30.0])
        backward(mul(column, row).sum())
        # d/d col[i] = sum over the three columns of row
        assert np.allclose(column.grad.numpy(), np.array([[60.0], [60.0]], dtype=np.float32), atol=1e-5)

    def test_scalar_operand_gets_scalar_gradient(self):
        left = tensor([1.0, 2.0]).requires_grad_(True)
        backward(mul(left, 3.0).sum())
        assert np.array_equal(left.grad.numpy(), np.full(2, 3.0, dtype=np.float32))


class TestMultiParentAccumulation:
    """When several consumers read one tensor, their gradients must add up."""

    def test_two_consumers_accumulate(self):
        t = tensor([1.0, 2.0]).requires_grad_(True)
        # d(sqrt(t) + t*t)/dt = 1/(2*sqrt(t)) + 2t
        backward(sqrt(t).sum() + mul(t, t).sum())
        expected = 0.5 / np.sqrt(np.array([1.0, 2.0], dtype=np.float32)) + 2 * np.array([1.0, 2.0], dtype=np.float32)
        assert np.allclose(t.grad.numpy(), expected, atol=1e-6)

    def test_three_consumers_accumulate(self):
        t = tensor([2.0]).requires_grad_(True)
        total = t.sum() + t.sum() * 2.0 + sqrt(t).sum()
        backward(total)
        # 1 + 2 + 1/(2*sqrt(2))
        assert np.allclose(t.grad.numpy(), np.array([3.0 + 1 / (2 * np.sqrt(2))], dtype=np.float32), atol=1e-6)

    def test_diamond_keeps_both_paths(self):
        left = tensor([1.0, 2.0]).requires_grad_(True)
        right = tensor([3.0, 4.0]).requires_grad_(True)
        # (a + b) * (a - b) = a^2 - b^2, so d/da = 2a and d/db = -2b
        backward(mul(add(left, right), sub(left, right)).sum())
        assert np.allclose(left.grad.numpy(), 2 * np.array([1.0, 2.0], dtype=np.float32), atol=1e-6)
        assert np.allclose(right.grad.numpy(), -2 * np.array([3.0, 4.0], dtype=np.float32), atol=1e-6)


class TestChainOfOperations:
    """Short chains, checked against closed-form derivatives."""

    def test_four_op_chain(self):
        values = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        t = tensor(values).requires_grad_(True)
        # f(t) = sum(sqrt(exp(t * 2)))
        backward(sqrt(exp(mul(t, 2.0))).sum())
        # df/dt = 0.5 * exp(2t)^-0.5 * exp(2t) * 2 = exp(2t) / sqrt(exp(2t))
        expected = np.exp(2 * values) / np.sqrt(np.exp(2 * values))
        assert np.allclose(t.grad.numpy(), expected, atol=1e-5)

    def test_mean_reduction_scales_by_count(self):
        values = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
        t = tensor(values).requires_grad_(True)
        backward(mean(t))
        assert np.allclose(t.grad.numpy(), np.full(4, 0.25, dtype=np.float32), atol=1e-6)

    def test_partial_reduction_sums_only_that_axis(self):
        values = np.arange(6, dtype=np.float32).reshape(2, 3)
        t = tensor(values).requires_grad_(True)
        backward(sum_op(t, dim=1).sum())
        expected = np.broadcast_to(np.ones((2, 1), dtype=np.float32), (2, 3))
        assert np.allclose(t.grad.numpy(), expected, atol=1e-6)

    def test_reduction_over_trailing_axis(self):
        values = np.arange(6, dtype=np.float32).reshape(2, 3)
        t = tensor(values).requires_grad_(True)
        backward(sum_op(t, dim=0).sum())
        # Every row contributes to every column, so each element gets 1.
        assert np.allclose(t.grad.numpy(), np.ones((2, 3), dtype=np.float32), atol=1e-6)

    def test_chained_partial_reductions(self):
        values = np.arange(6, dtype=np.float32).reshape(2, 3)
        t = tensor(values).requires_grad_(True)
        # sum_rows = (3,); sum over that axis hits each element once.
        backward(sum_op(sum_op(t, dim=1), dim=0))
        assert np.allclose(t.grad.numpy(), np.ones((2, 3), dtype=np.float32), atol=1e-6)


class TestBatchedMatmul:
    """A weight shared across batch and sequence must be summed over both."""

    @pytest.mark.parametrize(
        "shape_a,shape_b",
        [
            ((4, 2), (2, 3)),
            ((2, 5, 16), (16, 32)),
            ((2, 5, 16), (2, 16, 32)),
            ((2, 3, 4), (4, 5)),
            ((2, 2, 3, 4), (4, 5)),
            ((2, 3, 4), (4,)),
        ],
    )
    def test_matches_directional_derivative(self, shape_a, shape_b):
        """Check the gradients against the forward pass alone.

        A flat reference is only valid for the 2-D case, because a batched
        weight is shared across the batch and its gradient is a sum. The
        defining property is the directional derivative:
        ``<grad_a, dA> + <grad_b, dB> == <seed, d(a @ b)>``, which depends on
        nothing but the forward pass and so cannot be wrong in the same way.
        """
        rng = np.random.default_rng(0)
        a = rng.standard_normal(shape_a).astype(np.float32)
        b = rng.standard_normal(shape_b).astype(np.float32)

        ta = tensor(a).requires_grad_(True)
        tb = tensor(b).requires_grad_(True)
        out = matmul(ta, tb)
        seed = rng.standard_normal(out.shape.dims).astype(np.float32)
        backward(out, tensor(seed))

        da = rng.standard_normal(shape_a).astype(np.float32)
        db = rng.standard_normal(shape_b).astype(np.float32)

        lhs = float((ta.grad.numpy() * da).sum() + (tb.grad.numpy() * db).sum())
        # Exact first-order change of the output, not a finite difference.
        d_out = np.matmul(da, b) + np.matmul(a, db)
        rhs = float((seed * d_out).sum())
        assert lhs == pytest.approx(rhs, rel=1e-4, abs=1e-4)

    def test_gradients_have_the_operand_shapes(self):
        rng = np.random.default_rng(2)
        for shape_a, shape_b in [((2, 5, 16), (16, 32)), ((2, 5, 16), (2, 16, 32))]:
            ta = tensor(rng.standard_normal(shape_a).astype(np.float32)).requires_grad_(True)
            tb = tensor(rng.standard_normal(shape_b).astype(np.float32)).requires_grad_(True)
            out = matmul(ta, tb)
            backward(out, tensor(rng.standard_normal(out.shape.dims).astype(np.float32)))
            assert ta.grad.shape == ta.shape
            assert tb.grad.shape == tb.shape

    def test_vector_contraction(self):
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        m = np.arange(6, dtype=np.float32).reshape(3, 2)
        ta = tensor(a).requires_grad_(True)
        tm = tensor(m).requires_grad_(True)
        out = matmul(ta, tm)
        seed = np.ones((2,), dtype=np.float32)
        backward(out, tensor(seed))
        assert np.allclose(ta.grad.numpy(), seed @ m.T, atol=1e-5)
        assert np.allclose(tm.grad.numpy(), np.outer(a, seed), atol=1e-5)


class TestViewGradientRouting:
    """Views share memory, so their gradients must reach the base tensor."""

    def test_transpose_routes_gradient_back(self):
        base = tensor([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]).requires_grad_(True)
        backward(base.transpose(0, 1).sum())
        assert base.grad is not None
        assert np.allclose(base.grad.numpy(), np.ones((2, 3), dtype=np.float32))

    def test_reshape_routes_gradient_back(self):
        base = tensor(np.arange(6, dtype=np.float32).reshape(2, 3)).requires_grad_(True)
        backward(base.reshape(3, 2).sum())
        assert base.grad is not None
        assert np.allclose(base.grad.numpy(), np.ones((2, 3), dtype=np.float32))

    def test_permute_routes_gradient_back(self):
        values = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
        base = tensor(values).requires_grad_(True)
        backward(base.permute(2, 0, 1).sum())
        assert base.grad is not None
        assert np.allclose(base.grad.numpy(), np.ones((2, 3, 4), dtype=np.float32))

    def test_slice_gradient_is_zero_outside_the_slice(self):
        base = tensor(np.arange(12, dtype=np.float32).reshape(3, 4)).requires_grad_(True)
        backward(base[:, 1:3].sum())
        expected = np.zeros((3, 4), dtype=np.float32)
        expected[:, 1:3] = 1.0
        assert np.allclose(base.grad.numpy(), expected, atol=1e-6)

    def test_integer_index_gradient_has_no_excess_axis(self):
        base = tensor(np.arange(12, dtype=np.float32).reshape(3, 4)).requires_grad_(True)
        backward(base[1].sum())
        expected = np.zeros((3, 4), dtype=np.float32)
        expected[1] = 1.0
        assert np.allclose(base.grad.numpy(), expected, atol=1e-6)

    def test_squeeze_and_unsqueeze_round_trip_gradient(self):
        base = tensor(np.arange(6, dtype=np.float32).reshape(1, 6)).requires_grad_(True)
        backward(base.squeeze().unsqueeze(0).sum())
        assert np.allclose(base.grad.numpy(), np.ones((1, 6), dtype=np.float32), atol=1e-6)

    def test_narrow_gradient(self):
        base = tensor(np.arange(10, dtype=np.float32)).requires_grad_(True)
        backward(base.narrow(0, 2, 3).sum())
        expected = np.zeros(10, dtype=np.float32)
        expected[2:5] = 1.0
        assert np.allclose(base.grad.numpy(), expected, atol=1e-6)


class TestGradientAccumulation:
    """Repeated backward passes must add, not overwrite."""

    def test_second_backward_adds_to_the_first(self):
        t = tensor([1.0, 2.0]).requires_grad_(True)
        backward(t.sum(), retain_graph=True)
        backward(t.sum(), retain_graph=True)
        assert np.allclose(t.grad.numpy(), np.full(2, 2.0, dtype=np.float32))

    def test_accumulation_mixed_with_middle_ops(self):
        t = tensor([2.0, 3.0]).requires_grad_(True)
        backward(mul(t, t).sum(), retain_graph=True)
        backward(mul(t, t).sum(), retain_graph=True)
        # each pass contributes 2t, so two passes give 4t
        assert np.allclose(t.grad.numpy(), 4 * np.array([2.0, 3.0], dtype=np.float32), atol=1e-5)


class TestNoGrad:
    """Under no_grad the graph is not recorded and backward is a no-op."""

    def test_no_grad_records_no_node(self):
        t = tensor([1.0, 2.0]).requires_grad_(True)
        with no_grad():
            out = mul(t, t)
        assert out._grad_fn is None

    def test_graph_recording_resumes_after_no_grad(self):
        t = tensor([1.0, 2.0]).requires_grad_(True)
        with no_grad():
            mul(t, t)
        backward(mul(t, t).sum())
        assert t.grad is not None
        assert np.allclose(t.grad.numpy(), 2 * np.array([1.0, 2.0], dtype=np.float32), atol=1e-6)


class TestBackwardRequiresScalar:
    """A non-scalar output needs an explicit seed."""

    def test_non_scalar_without_seed_raises(self):
        t = tensor([[1.0, 2.0]]).requires_grad_(True)
        with pytest.raises(ValueError, match="grad_outputs"):
            backward(mul(t, t))

    def test_non_scalar_with_seed_works(self):
        t = tensor([[1.0, 2.0]]).requires_grad_(True)
        seed = np.array([[1.0, 1.0]], dtype=np.float32)
        backward(mul(t, t), tensor(seed))
        assert np.allclose(t.grad.numpy(), 2 * np.array([[1.0, 2.0]], dtype=np.float32), atol=1e-6)


class TestDeepChainNumerically:
    """A long chain verified numerically, the way a user would."""

    def test_eight_op_chain_matches_numerical(self):
        rng = np.random.default_rng(1)
        values = rng.uniform(0.4, 1.6, size=5).astype(np.float32)
        t = tensor(values).requires_grad_(True)

        def f():
            x = mul(t, 1.5)
            x = exp(x)
            x = sqrt(x)
            x = add(x, 0.5)
            x = log(x)
            x = neg(x)
            x = mul(x, t)
            return sum_op(x)

        results = check_gradients(f, [t])
        assert all(r.passed for r in results), results[0]
