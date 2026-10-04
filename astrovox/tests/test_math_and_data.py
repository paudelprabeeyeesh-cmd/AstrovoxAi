"""Tests for the math extensions and the data pipeline."""

import numpy as np
import pytest

from astrovox import tensor
from astrovox.autograd import backward, check_gradients
from astrovox.data import (
    BatchSampler,
    DataLoader,
    Dataset,
    DistributedSampler,
    RandomSampler,
    SequentialSampler,
    TensorDataset,
    default_collate,
    infinite_loader,
)
from astrovox.ops import math_ext as m


def rng_tensor(shape=(2, 3), seed=0, requires_grad=False):
    values = np.random.default_rng(seed).standard_normal(shape).astype(np.float32)
    return tensor(values, requires_grad=requires_grad)


class TestElementwiseMath:
    @pytest.mark.parametrize("fn,numpy_fn", [(m.sin, np.sin), (m.cos, np.cos), (m.tan, np.tan)])
    def test_trigonometry_matches_numpy(self, fn, numpy_fn):
        x = rng_tensor(seed=1)
        assert np.allclose(fn(x).numpy(), numpy_fn(x.numpy()), atol=1e-6)

    def test_absolute_and_sign(self):
        x = tensor(np.array([-2.0, 0.0, 3.0], dtype=np.float32))
        assert np.array_equal(m.absolute(x).numpy(), np.array([2.0, 0.0, 3.0], dtype=np.float32))
        assert np.array_equal(m.sign(x).numpy(), np.array([-1.0, 0.0, 1.0], dtype=np.float32))

    def test_clamp_bounds_values(self):
        x = tensor(np.array([-2.0, 0.5, 3.0], dtype=np.float32))
        assert np.allclose(m.clamp(x, 0.0, 1.0).numpy(), np.array([0.0, 0.5, 1.0], dtype=np.float32))
        assert np.allclose(m.clip(x, 0.0, 1.0).numpy(), m.clamp(x, 0.0, 1.0).numpy())

    def test_modulo(self):
        x = tensor(np.array([5.0, 7.0, -1.0], dtype=np.float32))
        assert np.allclose(m.modulo(x, 3.0).numpy(), np.mod(x.numpy(), 3.0), atol=1e-6)

    def test_round_is_not_differentiable(self):
        x = rng_tensor(requires_grad=True)
        loss = m.round_tensor(x).sum()
        backward(loss)
        assert np.array_equal(x.grad.numpy(), np.zeros_like(x.numpy()))

    def test_where_selects(self):
        mask = tensor(np.array([True, False]))
        a = tensor(np.array([1.0, 2.0], dtype=np.float32))
        b = tensor(np.array([3.0, 4.0], dtype=np.float32))
        assert np.allclose(m.where(mask, a, b).numpy(), np.array([1.0, 4.0], dtype=np.float32))

    @pytest.mark.parametrize("fn,numpy_fn", [(m.sin, np.sin), (m.cos, np.cos), (m.absolute, np.abs)])
    def test_gradients_match_numerical(self, fn, numpy_fn):
        x = rng_tensor((3,), seed=2, requires_grad=True)

        def loss():
            return (fn(x) * tensor(np.array([1.0, 2.0, 3.0], dtype=np.float32))).sum()

        results = check_gradients(loss, [x])
        assert all(r.passed for r in results), results[0]

    def test_clamp_gradient_is_zero_outside(self):
        x = tensor(np.array([-2.0, 0.5, 3.0], dtype=np.float32), requires_grad=True)
        m.clamp(x, 0.0, 1.0).sum().backward()
        assert np.allclose(x.grad.numpy(), np.array([0.0, 1.0, 0.0], dtype=np.float32))


class TestNormsAndDistances:
    def test_frobenius_norm(self):
        assert m.frobenius_norm(tensor(np.array([3.0, 4.0], dtype=np.float32))) == 5.0

    def test_vector_norm(self):
        x = rng_tensor((4,))
        assert float(m.vector_norm(x).numpy()) == pytest.approx(
            float(np.linalg.norm(x.numpy())), rel=1e-5
        )

    def test_cosine_similarity_of_identical_vectors_is_one(self):
        a = tensor(np.array([[1.0, 0.0]], dtype=np.float32))
        assert float(m.cosine_similarity(a, a).numpy()[0]) == pytest.approx(1.0, abs=1e-5)

    def test_cosine_similarity_of_orthogonal_is_zero(self):
        a = tensor(np.array([[1.0, 0.0]], dtype=np.float32))
        b = tensor(np.array([[0.0, 1.0]], dtype=np.float32))
        assert float(m.cosine_similarity(a, b).numpy()[0]) == pytest.approx(0.0, abs=1e-5)

    def test_euclidean_and_manhattan(self):
        a = tensor(np.array([[0.0, 0.0]], dtype=np.float32))
        b = tensor(np.array([[3.0, 4.0]], dtype=np.float32))
        assert float(m.euclidean_distance(a, b).numpy()[0]) == pytest.approx(5.0, rel=1e-5)
        assert float(m.manhattan_distance(a, b).numpy()[0]) == pytest.approx(7.0, rel=1e-5)

    def test_pairwise_distances_have_the_right_shape(self):
        a = rng_tensor((3, 4), seed=3)
        b = rng_tensor((2, 4), seed=4)
        assert tuple(m.pairwise_euclidean(a, b).shape.dims) == (3, 2)
        assert tuple(m.pairwise_cosine(a, b).shape.dims) == (3, 2)

    def test_pairwise_distance_of_a_point_with_itself_is_zero_on_the_diagonal(self):
        """Only the diagonal is zero: off-diagonal entries are real distances."""
        a = rng_tensor((3, 4), seed=5)
        distances = m.pairwise_euclidean(a, a).numpy()
        assert np.allclose(np.diag(distances), 0.0, atol=1e-5)
        assert (distances[~np.eye(3, dtype=bool)] > 0).all()


class TestLinearAlgebra:
    def test_inverse_round_trips(self):
        a = tensor(np.array([[4.0, 1.0], [1.0, 3.0]], dtype=np.float32))
        product = m.inverse(a).numpy() @ a.numpy()
        assert np.allclose(product, np.eye(2), atol=1e-5)

    def test_cholesky_reconstructs(self):
        a = tensor(np.array([[4.0, 1.0], [1.0, 3.0]], dtype=np.float32))
        lower = m.cholesky(a).numpy()
        assert np.allclose(lower @ lower.T, a.numpy(), atol=1e-5)

    def test_qr_shapes(self):
        q, r = m.qr(rng_tensor((3, 3), seed=6))
        assert tuple(q.shape.dims) == (3, 3)
        assert tuple(r.shape.dims) == (3, 3)

    def test_svd_shapes_and_reconstruction(self):
        a = rng_tensor((3, 2), seed=7)
        u, s, vt = m.svd(a)
        # A 3x2 matrix has min(3,2) singular values and thin factors.
        assert tuple(u.shape.dims) == (3, 2)
        assert tuple(s.shape.dims) == (2,)
        assert tuple(vt.shape.dims) == (2, 2)
        assert np.allclose((u.numpy() * s.numpy()) @ vt.numpy(), a.numpy(), atol=1e-4)


def test_lu_decomposition_or_clear_failure():
    """SciPy supplies LU; without it the error must say what is missing."""
    a = rng_tensor((3, 3), seed=8)
    try:
        lower, upper = m.lu(a)
    except ImportError as exc:
        assert "scipy" in str(exc).lower(), exc
        return
    assert tuple(lower.shape.dims) == (3, 3)
    assert tuple(upper.shape.dims) == (3, 3)

    def test_solve(self):
        a = tensor(np.array([[2.0, 0.0], [0.0, 4.0]], dtype=np.float32))
        b = tensor(np.array([[2.0], [8.0]], dtype=np.float32))
        assert np.allclose(m.solve(a, b).numpy(), np.array([[1.0], [2.0]], dtype=np.float32), atol=1e-5)

    def test_trace_and_determinant(self):
        a = tensor(np.array([[2.0, 1.0], [1.0, 3.0]], dtype=np.float32))
        assert m.trace(a) == pytest.approx(5.0)
        assert m.determinant(a) == pytest.approx(5.0)

    def test_fft_round_trip_is_lossless(self):
        signal = tensor(np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32))
        assert np.allclose(m.ifft(m.fft(signal)).numpy(), signal.numpy(), atol=1e-4)

    def test_fft_magnitude_matches_numpy(self):
        signal = tensor(np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32))
        assert np.allclose(m.fft_magnitude(signal).numpy(), np.abs(np.fft.fft(signal.numpy())), atol=1e-4)

    def test_logsumexp_matches_the_stable_formula(self):
        values = tensor(np.array([1.0, 2.0, 3.0], dtype=np.float32))
        peak = values.numpy().max()
        expected = np.log(np.exp(values.numpy() - peak).sum()) + peak
        assert float(m.logsumexp(values).numpy()) == pytest.approx(expected, rel=1e-6)


def sample_dataset(count: int = 10) -> Dataset:
    return Dataset(
        [
            (tensor(np.full(2, i, dtype=np.float32)), tensor(np.array([i % 3])))
            for i in range(count)
        ]
    )


class TestDatasets:
    def test_dataset_length_and_indexing(self):
        ds = sample_dataset(5)
        assert len(ds) == 5
        assert float(ds[0][0].numpy()[0]) == 0.0

    def test_dataset_iteration(self):
        assert len(list(sample_dataset(4))) == 4

    def test_feature_and_label_shape_discovery(self):
        ds = sample_dataset(3)
        assert ds.feature_shape == (2,)
        assert ds.label_shape == (1,)

    def test_shuffle_is_seeded_and_a_permutation(self):
        ds = sample_dataset(8)
        first = ds.shuffle(seed=1)
        second = ds.shuffle(seed=1)
        values = [float(s[0].numpy()[0]) for s in first.samples]
        assert values == [float(s[0].numpy()[0]) for s in second.samples]
        assert sorted(values) == [float(s[0].numpy()[0]) for s in ds.samples]

    def test_subset(self):
        assert len(sample_dataset(10).subset(4)) == 4

    def test_tensor_dataset(self):
        features = tensor(np.zeros((6, 3), dtype=np.float32))
        labels = tensor(np.arange(6).reshape(6, 1))
        ds = TensorDataset(features, labels)
        assert len(ds) == 6
        assert ds[0][0].shape.dims == (3,)


class TestSamplers:
    def test_sequential_sampler(self):
        assert list(SequentialSampler(5)) == [0, 1, 2, 3, 4]
        assert len(SequentialSampler(5)) == 5

    def test_random_sampler_is_a_permutation(self):
        indices = list(RandomSampler(10, seed=0))
        assert sorted(indices) == list(range(10))

    def test_random_sampler_is_reproducible(self):
        assert list(RandomSampler(10, seed=3)) == list(RandomSampler(10, seed=3))

    def test_random_sampler_with_replacement(self):
        indices = list(RandomSampler(8, seed=1, replacement=True))
        assert len(indices) == 8
        assert all(0 <= i < 8 for i in indices)

    @pytest.mark.parametrize("count", [0, 1, 7, 10, 13])
    def test_distributed_sampler_covers_everything_with_equal_shards(self, count):
        """Every rank gets the same count and the union covers the dataset.

        Padding deliberately repeats a few samples across ranks so the batch
        shape matches everywhere; what must hold is that a rank never sees the
        same index twice within itself.
        """
        replicas = 3
        shards = [
            list(DistributedSampler(count, replicas, rank=r, shuffle=False))
            for r in range(replicas)
        ]
        assert len({len(s) for s in shards}) == 1, [len(s) for s in shards]
        for shard in shards:
            assert len(set(shard)) == len(shard), "a rank received a repeated index"
        if count:
            assert set().union(*[set(s) for s in shards]) == set(range(count))

    def test_distributed_sampler_partitions_when_divisible(self):
        """With no padding needed the shards are a clean partition."""
        count, replicas = 9, 3
        shards = [
            list(DistributedSampler(count, replicas, rank=r, shuffle=False)) for r in range(replicas)
        ]
        assert sorted(i for s in shards for i in s) == list(range(count))
        for i in range(replicas):
            for j in range(i + 1, replicas):
                assert not set(shards[i]) & set(shards[j])

    def test_distributed_sampler_equalizes_length(self):
        shards = [len(DistributedSampler(10, 4, rank=r, shuffle=False)) for r in range(4)]
        assert len(set(shards)) == 1, shards

    def test_distributed_epoch_changes_order(self):
        sampler = DistributedSampler(10, 1, rank=0, seed=0, shuffle=True)
        first = list(sampler)
        sampler.set_epoch(1)
        assert list(sampler) != first

    def test_distributed_rejects_a_bad_rank(self):
        with pytest.raises(ValueError, match="rank"):
            DistributedSampler(10, num_replicas=2, rank=5)

    def test_batch_sampler_groups(self):
        batches = list(BatchSampler(SequentialSampler(10), 3))
        assert [len(b) for b in batches] == [3, 3, 3, 1]

    def test_batch_sampler_drop_last(self):
        batches = list(BatchSampler(SequentialSampler(10), 3, drop_last=True))
        assert [len(b) for b in batches] == [3, 3, 3]

    def test_batch_sampler_rejects_a_bad_size(self):
        with pytest.raises(ValueError, match="batch_size"):
            BatchSampler(SequentialSampler(4), 0)


def first_column(loader):
    """Return the first feature of every sample, in load order.

    Reading whole batches rather than batch starts is what makes ordering
    observable when there is only one batch.
    """
    out = []
    for features, _labels in loader:
        flat = features.numpy().reshape(len(features), -1)
        out.extend(float(v) for v in flat[:, 0])
    return out


class TestDataLoader:
    def test_yields_batches_of_the_right_size(self):
        loader = DataLoader(sample_dataset(10), batch_size=4)
        sizes = [b[0].shape.dims[0] for b in loader]
        assert sizes == [4, 4, 2]
        assert len(loader) == 3

    def test_drop_last_discards_the_partial_batch(self):
        loader = DataLoader(sample_dataset(10), batch_size=4, drop_last=True)
        assert [b[0].shape.dims[0] for b in loader] == [4, 4]

    def first_column(loader):
        """Return the first feature of every sample, in load order."""
        out = []
        for features, _labels in loader:
            out.extend(float(v) for v in features.numpy().reshape(len(features), -1)[:, 0])
        return out

    def test_shuffle_changes_the_order(self):
        ds = sample_dataset(10)
        ordered = first_column(DataLoader(ds, batch_size=2))
        shuffled = first_column(DataLoader(ds, batch_size=2, shuffle=True, seed=5))
        assert sorted(ordered) == sorted(shuffled), "shuffling must not lose samples"
        assert ordered != shuffled, "shuffling must change the order"

    def test_collate_stacks_tensors(self):
        batch = default_collate([tensor(np.array([i], dtype=np.float32)) for i in range(3)])
        assert tuple(batch.shape.dims) == (3, 1)

    def test_collate_keeps_heterogeneous_samples_as_a_list(self):
        assert default_collate([1, "a", None]) == [1, "a", None]

    def test_empty_collate(self):
        assert default_collate([]) == []

    def test_threaded_loading_matches_single_threaded(self):
        ds = sample_dataset(12)
        single = [b[0].numpy().copy() for b in DataLoader(ds, batch_size=3)]
        threaded = [b[0].numpy().copy() for b in DataLoader(ds, batch_size=3, num_workers=2)]
        assert len(single) == len(threaded)
        assert all(np.allclose(a, b) for a, b in zip(single, threaded))

    def test_threaded_loading_preserves_order(self):
        ds = sample_dataset(9)
        # first_column reads every sample, so this checks the full sequence.
        assert first_column(DataLoader(ds, batch_size=3, num_workers=3)) == [float(i) for i in range(9)]

    def test_rejects_bad_arguments(self):
        ds = sample_dataset(4)
        with pytest.raises(ValueError, match="batch_size"):
            DataLoader(ds, batch_size=0)
        with pytest.raises(ValueError, match="num_workers"):
            DataLoader(ds, num_workers=-1)

    def test_infinite_loader_keeps_producing(self):
        loader = DataLoader(sample_dataset(4), batch_size=2)
        stream = infinite_loader(loader)
        assert len([next(stream) for _ in range(6)]) == 6

    def test_a_loader_over_an_empty_dataset_yields_nothing(self):
        assert list(DataLoader(Dataset([]), batch_size=2)) == []
