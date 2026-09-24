import itertools
import math
import random


def _linspace(start, stop, num):
    if num == 1:
        yield start
    else:
        step = (stop - start) / (num - 1)
        for i in range(num):
            yield start + i * step


def grid_search(objective, param_ranges, resolution=10):
    best_params = None
    best_val = float("inf")
    ranges = [list(_linspace(*r, resolution)) for r in param_ranges]
    for combo in itertools.product(*ranges):
        val = objective(list(combo))
        if val < best_val:
            best_val = val
            best_params = list(combo)
    return best_params, best_val


def random_search(objective, param_ranges, max_iter=100):
    best_params = None
    best_val = float("inf")
    for _ in range(max_iter):
        params = [random.uniform(*r) for r in param_ranges]
        val = objective(params)
        if val < best_val:
            best_val = val
            best_params = params
    return best_params, best_val
