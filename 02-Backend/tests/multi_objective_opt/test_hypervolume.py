import numpy as np
from advanced_optimization.multi_objective_opt.hypervolume import hypervolume


def test_hypervolume_empty():
    assert hypervolume([], [0.0, 0.0]) == 0.0


def test_hypervolume_2d():
    front = np.array([[1.0, 1.0]])
    hv = hypervolume(front, [0.0, 0.0])
    assert hv == 1.0


def test_hypervolume_two_points():
    front = np.array([[1.0, 2.0], [2.0, 1.0]])
    hv = hypervolume(front, [0.0, 0.0])
    assert hv > 0.0


def test_hypervolume_reference_shift():
    front = np.array([[1.0, 1.0]])
    hv = hypervolume(front, [0.5, 0.5])
    assert hv == 0.25
