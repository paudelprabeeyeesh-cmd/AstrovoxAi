import numpy as np
from evolutionary_computation.particle_swarm import ParticleSwarmOptimizer, QuantumPSO


class TestParticleSwarmOptimizer:
    def setup_method(self):
        self.fitness_fn = lambda x: -np.sum(x ** 2)

    def test_init(self):
        pso = ParticleSwarmOptimizer(self.fitness_fn, n_particles=30, n_dimensions=5, bounds=(-1, 1))
        assert pso.positions.shape == (30, 5)

    def test_update(self):
        pso = ParticleSwarmOptimizer(self.fitness_fn, n_particles=30, n_dimensions=5, bounds=(-1, 1))
        fitness = pso.update()
        assert len(fitness) == 30

    def test_optimize(self):
        pso = ParticleSwarmOptimizer(self.fitness_fn, n_particles=30, n_dimensions=5, bounds=(-1, 1))
        best, fitness = pso.optimize(20)
        assert fitness <= 0
        assert len(pso.best_fitness_history) == 21


class TestQuantumPSO:
    def setup_method(self):
        self.fitness_fn = lambda x: -np.sum(x ** 2)

    def test_init(self):
        qpso = QuantumPSO(self.fitness_fn, n_particles=30, n_dimensions=5, bounds=(-1, 1))
        assert qpso.positions.shape == (30, 5)

    def test_update(self):
        qpso = QuantumPSO(self.fitness_fn, n_particles=30, n_dimensions=5, bounds=(-1, 1))
        fitness = qpso.update()
        assert len(fitness) == 30

    def test_optimize(self):
        qpso = QuantumPSO(self.fitness_fn, n_particles=30, n_dimensions=5, bounds=(-1, 1))
        best, fitness = qpso.optimize(20)
        assert fitness <= 0
