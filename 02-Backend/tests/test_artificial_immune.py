import numpy as np
from evolutionary_computation.artificial_immune import ArtificialImmuneSystem


class TestArtificialImmuneSystem:
    def setup_method(self):
        self.fitness_fn = lambda x: -np.sum(x ** 2)

    def test_init(self):
        ais = ArtificialImmuneSystem(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-1, 1))
        assert ais.population.shape == (20, 5)

    def test_evaluate(self):
        ais = ArtificialImmuneSystem(self.fitness_fn, population_size=10, n_dimensions=5, bounds=(-1, 1))
        fitness = ais.evaluate()
        assert len(fitness) == 10

    def test_affinity(self):
        ais = ArtificialImmuneSystem(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-1, 1))
        ind = np.ones(5)
        aff = ais.affinity(ind)
        assert aff <= 0

    def test_somatic_hypermutation(self):
        ais = ArtificialImmuneSystem(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-1, 1))
        ind = np.ones(5)
        mutated = ais.somatic_hypermutation(ind, affinity=1.0)
        assert mutated.shape == (5,)
        assert mutated.min() >= -1
        assert mutated.max() <= 1

    def test_clonal_selection(self):
        ais = ArtificialImmuneSystem(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-1, 1))
        new_pop = ais.clonal_selection()
        assert new_pop.shape[0] == 20

    def test_negative_selection(self):
        ais = ArtificialImmuneSystem(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-1, 1))
        ais.negative_selection()
        assert ais.population.shape[0] == 20

    def test_evolve(self):
        ais = ArtificialImmuneSystem(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-1, 1))
        best, fitness = ais.evolve(10)
        assert fitness <= 0
        assert ais.best_fitness_history[-1] == fitness
