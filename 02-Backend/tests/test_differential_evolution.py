import numpy as np
from evolutionary_computation.differential_evolution import DifferentialEvolution


class TestDifferentialEvolution:
    def setup_method(self):
        self.fitness_fn = lambda x: -np.sum(x ** 2)

    def test_init(self):
        de = DifferentialEvolution(self.fitness_fn, population_size=20, gene_length=5)
        assert de.population.shape == (20, 5)

    def test_evaluate(self):
        de = DifferentialEvolution(self.fitness_fn, population_size=10, gene_length=5)
        fitness = de.evaluate()
        assert len(fitness) == 10

    def test_rand1_mutation(self):
        de = DifferentialEvolution(self.fitness_fn, population_size=10, gene_length=5)
        mutant = de.rand1_mutation(0)
        assert mutant.shape == (5,)
        assert mutant.min() >= 0
        assert mutant.max() <= 1

    def test_best1_mutation(self):
        de = DifferentialEvolution(self.fitness_fn, population_size=10, gene_length=5)
        mutant = de.best1_mutation(0)
        assert mutant.shape == (5,)

    def test_current_to_best1_mutation(self):
        de = DifferentialEvolution(self.fitness_fn, population_size=10, gene_length=5)
        mutant = de.current_to_best1_mutation(0)
        assert mutant.shape == (5,)

    def test_crossover(self):
        de = DifferentialEvolution(self.fitness_fn, population_size=10, gene_length=5)
        trial = de.crossover(np.ones(5), np.zeros(5))
        assert trial.shape == (5,)

    def test_evolve_rand1(self):
        de = DifferentialEvolution(self.fitness_fn, population_size=20, gene_length=5)
        best, fitness = de.evolve(10)
        assert fitness <= 0

    def test_evolve_best1(self):
        de = DifferentialEvolution(self.fitness_fn, population_size=20, gene_length=5)
        best, fitness = de.evolve(10, mutation_fn="best1")
        assert fitness <= 0
