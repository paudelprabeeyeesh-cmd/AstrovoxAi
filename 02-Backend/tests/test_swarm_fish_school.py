import numpy as np
from swarm_intelligence.fish_school import FishSchoolSearch


def sphere(x: np.ndarray) -> float:
    return float(np.sum(x ** 2))


class TestFishSchoolSearch:
    def test_converges_near_zero(self):
        bounds = [(-5.0, 5.0), (-5.0, 5.0)]
        fss = FishSchoolSearch(sphere, bounds, n_fish=20, seed=42)
        best, best_fit, history = fss.optimize(30)
        assert best_fit < 0.5
        assert best.shape == (2,)

    def test_history_length(self):
        bounds = [(-5.0, 5.0)]
        fss = FishSchoolSearch(sphere, bounds, n_fish=10, seed=42)
        _, _, history = fss.optimize(20)
        assert len(history) == 21
