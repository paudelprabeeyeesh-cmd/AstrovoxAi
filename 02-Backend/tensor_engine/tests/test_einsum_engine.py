import numpy as np
import pytest
from tensor_engine.einsum_engine import EinsumEngine


class TestEinsumEngineInit:
    def test_default(self):
        engine = EinsumEngine()
        assert engine.default_optimize == "greedy"
        assert engine.cache_info()["size"] == 0

    def test_custom_default_optimize(self):
        engine = EinsumEngine(default_optimize="optimal")
        assert engine.default_optimize == "optimal"


class TestEinsumEngineCompute:
    def test_matmul(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        result = engine.compute("ij,jk->ik", A, B)
        expected = np.einsum("ij,jk->ik", A, B)
        np.testing.assert_allclose(result, expected)

    def test_compute_caches_shape(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        engine.compute("ij,jk->ik", A, B)
        info = engine.cache_info()
        assert info["size"] == 1

    def test_compute_reuses_cache(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        engine.compute("ij,jk->ik", A, B)
        info_before = engine.cache_info()["size"]
        engine.compute("ij,jk->ik", A, B)
        assert engine.cache_info()["size"] == info_before

    def test_compute_invalid_shapes(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(4, 5)
        with pytest.raises(ValueError):
            engine.compute("ij,jk->ik", A, B)

    def test_compute_invalid_operands(self):
        engine = EinsumEngine()
        with pytest.raises(ValueError):
            engine.compute("ij,jk->ik")

    def test_compute_trace(self):
        engine = EinsumEngine()
        A = np.random.randn(3, 3)
        result = engine.compute("ii->", A)
        expected = np.einsum("ii->", A)
        np.testing.assert_allclose(result, expected)

    def test_compute_outer_product(self):
        engine = EinsumEngine()
        a = np.random.randn(3)
        b = np.random.randn(4)
        result = engine.compute("i,j->ij", a, b)
        expected = np.einsum("i,j->ij", a, b)
        np.testing.assert_allclose(result, expected)

    def test_compute_hadamard(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(2, 3)
        result = engine.compute("ij,ij->ij", A, B)
        expected = np.einsum("ij,ij->ij", A, B)
        np.testing.assert_allclose(result, expected)

    def test_compute_custom_optimize(self):
        engine = EinsumEngine(default_optimize="optimal")
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        result = engine.compute("ij,jk->ik", A, B, optimize="optimal")
        expected = np.einsum("ij,jk->ik", A, B, optimize="optimal")
        np.testing.assert_allclose(result, expected)

    def test_compute_batch_matmul(self):
        engine = EinsumEngine()
        A = np.random.randn(5, 2, 3)
        B = np.random.randn(5, 3, 4)
        result = engine.compute("bij,bjk->bik", A, B)
        expected = np.einsum("bij,bjk->bik", A, B)
        np.testing.assert_allclose(result, expected)

    def test_compute_three_operands(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        C = np.random.randn(4, 5)
        result = engine.compute("ij,jk,kl->il", A, B, C)
        expected = np.einsum("ij,jk,kl->il", A, B, C)
        np.testing.assert_allclose(result, expected)

    def test_compute_diagonal_extraction(self):
        engine = EinsumEngine()
        A = np.random.randn(4, 4)
        result = engine.compute("ii->i", A)
        expected = np.einsum("ii->i", A)
        np.testing.assert_allclose(result, expected)

    def test_compute_sum_reduction(self):
        engine = EinsumEngine()
        A = np.random.randn(3, 4)
        result = engine.compute("ij->", A)
        expected = np.einsum("ij->", A)
        np.testing.assert_allclose(result, expected)

    def test_compute_mean_via_sum(self):
        engine = EinsumEngine()
        A = np.random.randn(3, 4)
        result = engine.compute("ij->", A)
        expected = np.einsum("ij->", A)
        np.testing.assert_allclose(result, expected)
        assert np.isclose(result, A.sum())

    def test_compute_cache_miss_different_shapes(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        engine.compute("ij,jk->ik", A, B)
        assert engine.cache_info()["size"] == 1
        C = np.random.randn(4, 5)
        engine.compute("ij,jk->ik", B, C)
        assert engine.cache_info()["size"] == 2


class TestEinsumEngineShape:
    def test_shape_basic(self):
        engine = EinsumEngine()
        shape = engine.shape("ij,jk->ik", (2, 3), (3, 4))
        assert shape == (2, 4)

    def test_shape_batch_matmul(self):
        engine = EinsumEngine()
        shape = engine.shape("bij,bjk->bik", (5, 2, 3), (5, 3, 4))
        assert shape == (5, 2, 4)

    def test_shape_invalid_shapes(self):
        engine = EinsumEngine()
        with pytest.raises(ValueError):
            engine.shape("ij,jk->ik", (2, 3), (4, 5))

    def test_shape_no_output(self):
        engine = EinsumEngine()
        shape = engine.shape("ij,jk", (2, 3), (3, 4))
        assert shape == ()

    def test_shape_outer_product(self):
        engine = EinsumEngine()
        shape = engine.shape("i,j->ij", (3,), (4,))
        assert shape == (3, 4)

    def test_shape_trace(self):
        engine = EinsumEngine()
        shape = engine.shape("ii->", (3, 3))
        assert shape == ()

    def test_shape_diagonal(self):
        engine = EinsumEngine()
        shape = engine.shape("ii->i", (4, 4))
        assert shape == (4,)

    def test_shape_three_operands(self):
        engine = EinsumEngine()
        shape = engine.shape("ij,jk,kl->il", (2, 3), (3, 4), (4, 5))
        assert shape == (2, 5)


class TestEinsumEngineOptimize:
    def test_optimize_path_contract_labels(self):
        engine = EinsumEngine()
        labels = engine.optimize_path("ij,jk->ik", (2, 3), (3, 4))
        assert "j" in labels

    def test_optimize_path_batch(self):
        engine = EinsumEngine()
        labels = engine.optimize_path("bij,bjk->bik", (5, 2, 3), (5, 3, 4))
        assert "j" in labels

    def test_optimize_path_no_contraction(self):
        engine = EinsumEngine()
        labels = engine.optimize_path("i,j->ij", (3,), (4,))
        assert labels == []

    def test_optimize_path_trace(self):
        engine = EinsumEngine()
        labels = engine.optimize_path("ii->", (3, 3))
        assert "i" in labels


class TestEinsumEngineCache:
    def test_clear_cache(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        engine.compute("ij,jk->ik", A, B)
        assert engine.cache_info()["size"] == 1
        engine.clear_cache()
        assert engine.cache_info()["size"] == 0

    def test_cache_info_keys(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        engine.compute("ij,jk->ik", A, B)
        info = engine.cache_info()
        assert "keys" in info
        assert len(info["keys"]) == 1

    def test_cache_different_equations(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        engine.compute("ij,jk->ik", A, B)
        engine.compute("ij,jk->ji", A, B)
        assert engine.cache_info()["size"] == 2

    def test_cache_same_equation_same_shapes_reuses(self):
        engine = EinsumEngine()
        A = np.random.randn(2, 3)
        B = np.random.randn(3, 4)
        engine.compute("ij,jk->ik", A, B)
        engine.compute("ij,jk->ik", A, B)
        assert engine.cache_info()["size"] == 1

    def test_cache_key_format(self):
        engine = EinsumEngine()
        A = np.zeros((2, 3))
        B = np.zeros((3, 4))
        engine.compute("ij,jk->ik", A, B)
        key = engine.cache_info()["keys"][0]
        assert "ij,jk->ik" in key
