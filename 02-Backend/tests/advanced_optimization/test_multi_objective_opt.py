import numpy as np
from advanced_optimization.multi_objective_opt import NSGA2, pareto_front, dominates


def test_dominates():
    a = np.array([1.0, 2.0])
    b = np.array([2.0, 3.0])
    assert dominates(a, b)
    assert not dominates(b, a)


def test_pareto_front_basic():
    objs = np.array([[1.0, 2.0], [2.0, 1.0], [3.0, 3.0]])
    front = pareto_front(range(len(objs)), objs)
    assert 0 in front
    assert 1 in front
    assert 2 not in front


def test_nsga2_runs():
    def obj1(x):
        return np.sum(x ** 2)
    def obj2(x):
        return np.sum((x - 2) ** 2)
    def objs(x):
        return np.array([obj1(x), obj2(x)])
    bounds = [(-5, 5), (-5, 5)]
    opt = NSGA2(pop_size=20, max_iter=10)
    pop = opt.optimize(objs, bounds)
    assert pop.shape[1] == 2
