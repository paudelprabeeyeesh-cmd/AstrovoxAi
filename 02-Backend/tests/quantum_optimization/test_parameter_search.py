from quantum_optimization.parameter_search import grid_search, random_search


def test_grid_search():
    f = lambda x: sum((xi - 1.0) ** 2 for xi in x)
    best_params, best_val = grid_search(f, [(-2, 2), (-2, 2)], resolution=5)
    assert len(best_params) == 2
    assert abs(best_params[0] - 1.0) < 0.5
    assert abs(best_params[1] - 1.0) < 0.5


def test_random_search():
    f = lambda x: sum((xi - 1.0) ** 2 for xi in x)
    best_params, best_val = random_search(f, [(-2, 2), (-2, 2)], max_iter=50)
    assert len(best_params) == 2
    assert abs(best_params[0] - 1.0) < 1.0
    assert abs(best_params[1] - 1.0) < 1.0
