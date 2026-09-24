import numpy as np
import pytest

from tensor_engine.einsum_engine import EinsumEngine
from tensor_engine.einsum import EinsumEquation, einsum


def test_einsum_engine_compute():
    engine = EinsumEngine()
    a = np.random.rand(3, 4)
    b = np.random.rand(4, 5)
    result = engine.compute("ij,jk->ik", a, b)
    expected = np.einsum("ij,jk->ik", a, b)
    np.testing.assert_array_almost_equal(result, expected)


def test_einsum_engine_shape():
    engine = EinsumEngine()
    shape = engine.shape("ij,jk->ik", (3, 4), (4, 5))
    assert shape == (3, 5)


def test_einsum_engine_optimize_path():
    engine = EinsumEngine()
    labels = engine.optimize_path("ij,jk,kl->il", (3, 4), (4, 5), (5, 6))
    assert isinstance(labels, list)


def test_einsum_engine_cache():
    engine = EinsumEngine()
    a = np.random.rand(2, 3)
    engine.compute("ij->ji", a)
    info = engine.cache_info()
    assert info["size"] == 1
    engine.clear_cache()
    assert engine.cache_info()["size"] == 0


def test_einsum_equation_verify_shapes():
    eq = EinsumEquation("ij,jk->ik")
    eq.verify_shapes([(3, 4), (4, 5)])


def test_einsum_equation_bad_shapes():
    eq = EinsumEquation("ij,jk->ik")
    with pytest.raises(ValueError):
        eq.verify_shapes([(3, 4), (5, 6)])


def test_einsum_function():
    a = np.random.rand(2, 3)
    b = np.random.rand(3, 4)
    result = einsum("ij,jk->ik", a, b)
    expected = np.einsum("ij,jk->ik", a, b)
    np.testing.assert_array_almost_equal(result, expected)
