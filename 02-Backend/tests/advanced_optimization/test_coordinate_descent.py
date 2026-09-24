import numpy as np
import pytest
from advanced_optimization.coordinate_descent import (
    cyclic_coordinate_descent,
    gauss_southwell,
    block_coordinate_descent,
)


def test_cyclic_coordinate_descent():
    f = lambda x: np.sum((x - 2) ** 2)
    grad_f = lambda x: 2 * (x - 2)
    x = cyclic_coordinate_descent(f, grad_f, np.array([0.0]), max_iter=100)
    assert np.allclose(x, 2.0, atol=0.5)


def test_gauss_southwell():
    f = lambda x: np.sum((x - 3) ** 2)
    grad_f = lambda x: 2 * (x - 3)
    x = gauss_southwell(f, grad_f, np.array([0.0]), max_iter=100)
    assert np.allclose(x, 3.0, atol=0.5)


def test_block_coordinate_descent():
    f = lambda x: np.sum((x - np.array([1.0, 2.0])) ** 2)
    grad_f = lambda x: 2 * (x - np.array([1.0, 2.0]))
    x = block_coordinate_descent(f, grad_f, np.array([0.0, 0.0]), blocks=[[0], [1]], max_iter=100)
    assert np.allclose(x, np.array([1.0, 2.0]), atol=0.5)
