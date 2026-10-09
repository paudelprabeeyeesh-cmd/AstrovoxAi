import numpy as np
from advanced_optimization.multi_objective_opt.epsilon_lexicase import EpsilonLexicase


def test_select_returns_valid():
    pop = np.array([[0.0, 0.0], [1.0, 1.0]])
    objs = np.array([[0.0, 0.0], [1.0, 1.0]])
    selector = EpsilonLexicase(epsilon=0.0)
    for _ in range(10):
        idx = selector.select(pop, objs)
        assert any(np.array_equal(idx, p) for p in pop)


def test_epsilon_zero_selects_best():
    pop = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
    objs = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
    selector = EpsilonLexicase(epsilon=0.0)
    selected = [selector.select(pop, objs) for _ in range(100)]
    assert all(np.array_equal(s, [0.0, 0.0]) for s in selected)


def test_epsilon_large_allows_all():
    pop = np.array([[0.0, 0.0], [1.0, 1.0]])
    objs = np.array([[0.0, 0.0], [1.0, 1.0]])
    selector = EpsilonLexicase(epsilon=10.0)
    selected = [selector.select(pop, objs) for _ in range(50)]
    unique = {tuple(s) for s in selected}
    assert len(unique) == 2
