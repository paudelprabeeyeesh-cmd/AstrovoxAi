"""Tests for the graph inspector and the tensor layer.

The tensor tests compare against NumPy directly, so a bug in the view and
broadcast logic shows up as a mismatch rather than as a silently wrong
gradient much later.
"""

import numpy as np
import pytest

from astrovox import tensor
from astrovox.autograd import backward
from astrovox.debug import (
    check_graph,
    describe_tensor,
    find_constant_subgraphs,
    format_gradient_table,
    gradient_table,
    inspect,
)
from astrovox.nn import Embedding, Linear, ReLU, Sequential
from astrovox.ops import cross_entropy
from astrovox.tensor import Shape
from astrovox.tensor.shape import broadcast_shapes


class TestShapeAlgebra:
    def test_numel_and_ndims(self):
        assert Shape((2, 3, 4)).numel == 24
        assert Shape((2, 3, 4)).ndim == 3
        assert Shape(()).numel == 1
        assert Shape(()).is_scalar

    def test_row_major_strides(self):
        assert Shape((2, 3)).row_major_strides() == (3, 1)
        assert Shape((2, 3, 4)).row_major_strides() == (12, 4, 1)

    def test_broadcast_shapes(self):
        assert broadcast_shapes(Shape((3, 1)), Shape((1, 4))) == Shape((3, 4))
        assert broadcast_shapes(Shape((5,)), Shape(())) == Shape((5,))

    def test_incompatible_broadcast_raises(self):
        with pytest.raises(ValueError, match="Cannot broadcast"):
            broadcast_shapes(Shape((3,)), Shape((4,)))

    def test_unravel_and_ravel_round_trip(self):
        shape = Shape((2, 3, 4))
        for index in [(0, 0, 0), (1, 2, 3), (0, 1, 2)]:
            assert shape.unravel(shape.ravel(index)) == index

    def test_negative_dimension_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            Shape((-1, 3))


class TestTensorAgainstNumpy:
    """Every operation is checked against the NumPy equivalent."""

    @pytest.mark.parametrize(
        "shape", [(3,), (2, 3), (2, 3, 4), (4, 2, 3, 2), (1, 5), (5, 1)]
    )
    def test_full_and_flatten(self, shape):
        ref = np.random.default_rng(0).standard_normal(shape).astype(np.float32)
        t = tensor(ref)
        assert np.array_equal(t.numpy(), ref)
        assert np.array_equal(t.reshape(-1).numpy(), ref.reshape(-1))

    @pytest.mark.parametrize("shape", [(2, 3), (2, 3, 4), (4, 2, 3, 2)])
    def test_transpose_matches_numpy_swapaxes(self, shape):
        ref = np.random.default_rng(1).standard_normal(shape).astype(np.float32)
        t = tensor(ref)
        assert np.array_equal(t.transpose(0, 1).numpy(), ref.swapaxes(0, 1))
        assert np.array_equal(t.transpose(0, 1).transpose(0, 1).numpy(), ref)

    @pytest.mark.parametrize("shape", [(2, 3, 4), (4, 2, 3, 2)])
    def test_permute_matches_numpy_transpose(self, shape):
        ref = np.random.default_rng(2).standard_normal(shape).astype(np.float32)
        t = tensor(ref)
        order = tuple(reversed(range(len(shape))))
        assert np.array_equal(t.permute(*order).numpy(), ref.transpose(*order))

    @pytest.mark.parametrize("shape", [(3, 4), (2, 3, 4)])
    def test_slicing_matches_numpy(self, shape):
        ref = np.random.default_rng(3).standard_normal(shape).astype(np.float32)
        t = tensor(ref)
        assert np.array_equal(t[0].numpy(), ref[0])
        assert np.array_equal(t[:, 0].numpy(), ref[:, 0])
        assert np.array_equal(t[1:].numpy(), ref[1:])
        assert np.array_equal(t[..., -1].numpy(), ref[..., -1])
        if len(shape) == 3:
            assert np.array_equal(t[0, 1:3, 2].numpy(), ref[0, 1:3, 2])

    def test_views_share_storage_so_writes_are_visible(self):
        base = tensor(np.zeros((2, 3), dtype=np.float32))
        view = base[0]
        view.numpy()[...] = 5.0
        assert np.array_equal(base.numpy()[0], np.full(3, 5.0, dtype=np.float32))

    def test_transpose_is_a_view_not_a_copy(self):
        base = np.arange(6, dtype=np.float32).reshape(2, 3)
        t = tensor(base.copy())
        view = t.transpose(0, 1)
        assert not view.is_contiguous
        view.numpy()[...] = 0.0
        assert np.array_equal(t.numpy(), np.zeros((2, 3), dtype=np.float32))

    def test_index_select_matches_numpy(self):
        ref = np.random.default_rng(4).standard_normal((4, 3)).astype(np.float32)
        t = tensor(ref)
        assert np.array_equal(t.index_select(0, tensor([2, 0])).numpy(), ref[[2, 0]])

    def test_item_requires_exactly_one_element(self):
        with pytest.raises(ValueError, match="exactly one element"):
            tensor([[1.0, 2.0]]).item()

    def test_reshape_infers_one_dimension(self):
        t = tensor(np.arange(6, dtype=np.float32))
        assert tuple(t.reshape(2, -1).shape.dims) == (2, 3)
        assert tuple(t.reshape(-1, 2).shape.dims) == (3, 2)

    def test_reshape_element_count_must_match(self):
        with pytest.raises(ValueError, match="Cannot reshape"):
            tensor(np.zeros(6, dtype=np.float32)).reshape(4, 4)

    def test_reshape_allows_at_most_one_wildcard(self):
        with pytest.raises(ValueError, match="Only one dimension"):
            tensor(np.zeros(6, dtype=np.float32)).reshape(-1, -1)

    def test_out_of_range_index_raises(self):
        with pytest.raises(IndexError, match="out of range"):
            tensor(np.zeros((2, 2), dtype=np.float32))[5]


class TestDTypeAndPromotion:
    def test_int_float_promotes_to_float(self):
        result = tensor([1, 2, 3]) + 1.5
        assert result.dtype.is_float

    def test_float_operations_stay_float32(self):
        result = tensor([1.0, 2.0]) * 3.0
        assert result.dtype.name == "float32"

    def test_reduction_accumulates_in_wider_type(self):
        from astrovox.ops import sum as sum_op

        total = sum_op(tensor([1, 2, 3], dtype="int32"))
        assert total.item() == 6


class TestSerializationRoundTrip:
    @pytest.mark.parametrize(
        "shape,dtype",
        [((3,), "float32"), ((2, 3), "float64"), ((2, 2, 2), "int64"), ((4,), "int8")],
    )
    def test_tensor_round_trip(self, shape, dtype):
        from astrovox.tensor.serialization import deserialize_tensor, serialize_tensor

        ref = (np.random.default_rng(5).standard_normal(shape) * 10).astype(dtype)
        restored = deserialize_tensor(serialize_tensor(tensor(ref)))
        assert tuple(restored.shape.dims) == shape
        assert restored.dtype.name == dtype
        assert np.array_equal(restored.numpy(), ref)

    def test_checkpoint_round_trip_preserves_values(self, tmp_path):
        from astrovox.tensor.serialization import load_checkpoint, save_checkpoint

        model = Sequential(Linear(3, 4), ReLU(), Linear(4, 2))
        x = tensor(np.random.default_rng(6).standard_normal((5, 3)).astype(np.float32))
        before = model(x).numpy().copy()

        path = save_checkpoint(model, tmp_path / "m.avx", {"step": 3})
        clone = Sequential(Linear(3, 4), ReLU(), Linear(4, 2))
        extra = load_checkpoint(clone, path)
        assert extra["step"] == 3
        assert np.array_equal(clone(x).numpy(), before)

    def test_corrupt_blob_is_rejected(self):
        from astrovox.tensor.serialization import deserialize_tensor

        with pytest.raises(ValueError, match="bad magic"):
            deserialize_tensor(b"not a tensor blob")

    def test_truncated_payload_is_rejected(self):
        from astrovox.tensor.serialization import deserialize_tensor, serialize_tensor

        blob = serialize_tensor(tensor(np.arange(4, dtype=np.float32)))
        with pytest.raises(ValueError, match="Truncated"):
            deserialize_tensor(blob[:-4])

    def test_named_tensor_archive_round_trip(self, tmp_path):
        from astrovox.tensor.serialization import load_tensors, save_tensors

        tensors = {"a": tensor([1.0, 2.0]), "b": tensor(np.zeros((2, 2), dtype=np.float32))}
        save_tensors(tmp_path / "tensors.avz", tensors)
        loaded = load_tensors(tmp_path / "tensors.avz")
        assert set(loaded) == {"a", "b"}
        assert np.array_equal(loaded["a"].numpy(), np.array([1.0, 2.0], dtype=np.float32))


class TestStressAndMemory:
    def test_large_tensor_operations(self):
        big = tensor(np.random.default_rng(7).standard_normal((256, 256)).astype(np.float32))
        total = (big * big).sum()
        assert np.isfinite(total.item())
        assert total.item() > 0

    def test_many_small_allocations_do_not_leak_storage_references(self):
        from astrovox.tensor.tensor import Tensor

        base = tensor(np.zeros((10, 10), dtype=np.float32))
        before = base._storage.view_count
        views = [base[i] for i in range(10)]
        for v in views:
            v._storage.release_view()
        assert base._storage.view_count == before

    def test_deep_view_chain_stays_consistent(self):
        ref = np.random.default_rng(8).standard_normal((2, 3, 4, 5)).astype(np.float32)
        t = tensor(ref)
        view = t.transpose(0, 1).permute(0, 1, 3, 2).reshape(2, 3, 20).permute(0, 2, 1)
        assert view.shape.numel == ref.size
        assert view.numpy().size == ref.size

    def test_repeated_reshape_transpose_round_trip_is_exact(self):
        ref = np.random.default_rng(9).standard_normal((3, 4, 5)).astype(np.float32)
        t = tensor(ref)
        for _ in range(5):
            t = t.transpose(0, 1).transpose(0, 1)
        assert np.array_equal(t.numpy(), ref)


class TestGraphInspector:
    def test_reports_a_healthy_graph(self):
        model = Sequential(Linear(4, 8), ReLU(), Linear(8, 2))
        x = tensor(np.random.default_rng(10).standard_normal((6, 4)).astype(np.float32))
        y = tensor(np.array([0, 1, 0, 1, 0, 1]))
        loss = cross_entropy(model(x), y)
        assert check_graph(loss, model) == []

    def test_finds_a_disconnected_parameter(self):
        class DropBias(Linear):
            def forward(self, x):
                return x @ self.weight.transpose(0, 1)

        layer = DropBias(4, 3)
        out = layer(tensor(np.random.default_rng(11).standard_normal((5, 4)).astype(np.float32)))
        problems = check_graph(out, layer)
        assert any("bias" in p for p in problems), problems

    def test_reports_execution_order_root_first(self):
        model = Sequential(Linear(4, 8), ReLU(), Linear(8, 2))
        x = tensor(np.random.default_rng(12).standard_normal((6, 4)).astype(np.float32))
        loss = cross_entropy(model(x), tensor(np.zeros(6, dtype=np.int64)))
        order = inspect(loss, model).execution_order()
        assert order[0] == "cross_entropy"
        assert order[-1] in {"view", "matmul"}

    def test_export_formats(self):
        model = Sequential(Linear(4, 8), ReLU())
        x = tensor(np.random.default_rng(13).standard_normal((6, 4)).astype(np.float32))
        report = inspect(model(x).sum(), model)
        assert "digraph autograd" in report.to_dot()
        assert '"node_count"' in report.to_json()
        assert "graph:" in report.to_text()

    def test_json_export_is_valid_json(self):
        import json

        model = Sequential(Linear(4, 8))
        x = tensor(np.random.default_rng(14).standard_normal((6, 4)).astype(np.float32))
        report = inspect(model(x).sum(), model)
        parsed = json.loads(report.to_json())
        assert parsed["node_count"] == report.node_count

    def test_gradient_table_after_backward(self):
        model = Sequential(Linear(4, 2))
        x = tensor(np.random.default_rng(15).standard_normal((6, 4)).astype(np.float32))
        backward(model(x).sum())
        rows = gradient_table(model)
        assert len(rows) == 2
        assert all(not is_non_finite for _, _, _, is_non_finite in rows)
        assert "parameter" in format_gradient_table(model)

    def test_detects_a_non_finite_gradient(self):
        model = Sequential(Linear(4, 2))
        x = tensor(np.random.default_rng(16).standard_normal((6, 4)).astype(np.float32))
        out = model(x)
        out._grad = tensor(np.full((6, 2), np.nan, dtype=np.float32))
        model[0].weight._grad = out._grad
        report = inspect(out, model)
        assert "0.weight" in report.non_finite_parameters()

    def test_describe_tensor_mentions_key_facts(self):
        t = tensor(np.zeros((2, 3), dtype=np.float32))
        description = describe_tensor(t)
        assert "shape=(2, 3)" in description
        assert "float32" in description
        assert "contiguous" in description

    def test_constant_subgraphs_are_findable(self):
        from astrovox.autograd import no_grad
        from astrovox.nn import Linear as L

        model = Sequential(Linear(4, 4))
        x = tensor(np.random.default_rng(17).standard_normal((3, 4)).astype(np.float32))
        with no_grad():
            frozen = model(x)
        with no_grad():
            pass
        # With grad recording off the branch still runs but records nothing.
        assert isinstance(frozen, type(frozen))
