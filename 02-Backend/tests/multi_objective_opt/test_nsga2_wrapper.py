import numpy as np
from advanced_optimization.multi_objective_opt.nsga2_wrapper import NSGA2


def test_nsga2_runs():
    def objs(x):
        return np.array([np.sum(x ** 2), np.sum((x - 2) ** 2)])
    bounds = [(-5, 5), (-5, 5)]
    opt = NSGA2(pop_size=20, max_iter=10)
    pop = opt.optimize(objs, bounds)
    assert pop.shape[1] == 2
    assert pop.shape[0] == 20


def test_nsga2_single_dimension():
    def objs(x):
        return np.array([x[0] ** 2])
    bounds = [(-5, 5)]
    opt = NSGA2(pop_size=10, max_iter=5)
    pop = opt.optimize(objs, bounds)
    assert pop.shape[1] == 1
    assert pop.shape[0] == 10
