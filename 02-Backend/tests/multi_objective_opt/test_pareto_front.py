import numpy as np
from advanced_optimization.multi_objective_opt.pareto_front import (
    dominates,
    non_dominated_sort,
    crowding_distance,
    pareto_front,
)


def test_dominates_basic():
    a = np.array([1.0, 2.0])
    b = np.array([2.0, 3.0])
    assert dominates(a, b)
    assert not dominates(b, a)


def test_dominates_tie():
    a = np.array([1.0, 2.0])
    b = np.array([1.0, 2.0])
    assert not dominates(a, b)


def test_non_dominated_sort_basic():
    objs = np.array([[1.0, 2.0], [2.0, 1.0], [3.0, 3.0]])
    fronts = non_dominated_sort(range(len(objs)), objs)
    assert fronts[0] == [0, 1]
    assert fronts[1] == [2]


def test_crowding_distance():
    objs = np.array([[1.0, 2.0], [2.0, 1.0], [3.0, 3.0]])
    front = [0, 1]
    distances = crowding_distance(front, objs)
    assert len(distances) == 2
    assert distances[0] == float("inf")
    assert distances[1] == float("inf")


def test_pareto_front_basic():
    objs = np.array([[1.0, 2.0], [2.0, 1.0], [3.0, 3.0]])
    front = pareto_front(range(len(objs)), objs)
    assert set(front) == {0, 1}
