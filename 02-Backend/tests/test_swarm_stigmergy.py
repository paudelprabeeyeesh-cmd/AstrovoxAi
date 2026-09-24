from swarm_intelligence.stigmergy import StigmergySimulation


class TestStigmergy:
    def test_paths_generated(self):
        sim = StigmergySimulation(10, 10, 3, (0, 0), (9, 9), seed=42)
        paths = sim.run(n_iterations=5, max_steps=50)
        assert len(paths) == 3 * 5

    def test_grid_evaporation(self):
        sim = StigmergySimulation(5, 5, 1, (0, 0), (4, 4), seed=42)
        before = sim.grid.grid.max()
        sim.grid.evaporate()
        after = sim.grid.grid.max()
        assert after <= before + 1e-6

    def test_deposit_increases(self):
        sim = StigmergySimulation(5, 5, 1, (0, 0), (4, 4), seed=42)
        sim.grid.deposit(2, 2, 1.0)
        assert sim.grid.grid[2, 2] >= 1.0 - 1e-6
