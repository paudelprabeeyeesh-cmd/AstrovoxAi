import numpy as np
import pytest
from swarm_intelligence.insect_colony import InsectColony


class TestInsectColony:
    def test_allocate_returns_counts(self):
        colony = InsectColony(10, ["forage", "nurse", "defend"], seed=42)
        counts = colony.allocate(noise=0.0)
        assert set(counts.keys()) == {"forage", "nurse", "defend"}
        assert sum(counts.values()) <= 10

    def test_efficiency_in_range(self):
        colony = InsectColony(10, ["forage", "nurse"], seed=42)
        colony.allocate(noise=0.0)
        eff = colony.efficiency({"forage": 5, "nurse": 3})
        assert 0.0 <= eff <= 1.0

    def test_optimize_returns_history(self):
        colony = InsectColony(10, ["forage", "nurse"], seed=42)
        hist = colony.optimize({"forage": 5, "nurse": 3}, iterations=10)
        assert len(hist) == 10
