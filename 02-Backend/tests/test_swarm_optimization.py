import numpy as np
import pytest
from swarm_intelligence.swarm_optimization import SwarmOptimization


def sphere(x: np.ndarray) -> float:
    return float(np.sum(x ** 2))


class TestSwarmOptimization:
    def test_converges_near_zero(self):
        bounds = [(-5.0, 5.0), (-5.0, 5.0)]
        opt = SwarmOptimization(sphere, bounds, n_particles=20, seed=42)
        best, best_fit, history = opt.optimize(50)
        assert best_fit < 1e-3
        assert best.shape == (2,)

    def test_history_length(self):
        bounds = [(-5.0, 5.0)]
        opt = SwarmOptimization(sphere, bounds, n_particles=10, seed=42)
        _, _, history = opt.optimize(30)
        assert len(history) == 31

    def test_improves_over_time(self):
        bounds = [(-5.0, 5.0)]
        opt = SwarmOptimization(sphere, bounds, n_particles=15, seed=42)
        _, _, history = opt.optimize(40)
        assert history[0] >= history[-1] - 1e-6
