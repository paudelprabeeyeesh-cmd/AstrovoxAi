import numpy as np
from swarm_intelligence.bee_algorithm import BeeColonyOptimization


def sphere(x: np.ndarray) -> float:
    return float(np.sum(x ** 2))


class TestBeeColonyOptimization:
    def test_converges_near_zero(self):
        bounds = [(-5.0, 5.0), (-5.0, 5.0)]
        abc = BeeColonyOptimization(sphere, bounds, n_bees=20, seed=42)
        best, best_fit, history = abc.optimize(30)
        assert best_fit < 1e-3
        assert best.shape == (2,)

    def test_history_nonempty(self):
        bounds = [(-5.0, 5.0)]
        abc = BeeColonyOptimization(sphere, bounds, n_bees=15, seed=42)
        _, _, history = abc.optimize(20)
        assert len(history) == 20
