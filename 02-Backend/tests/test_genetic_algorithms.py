import numpy as np
from evolutionary_computation.genetic_algorithms import GeneticAlgorithm


class TestGeneticAlgorithm:
    def setup_method(self):
        self.fitness_fn = lambda x: -np.sum(x ** 2)

    def test_init(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=20, gene_length=5)
        assert ga.population.shape == (20, 5)

    def test_evaluate(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=10, gene_length=5)
        fitness = ga.evaluate()
        assert len(fitness) == 10
        assert all(f <= 0 for f in fitness)

    def test_tournament_selection(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=10, gene_length=5)
        selected = ga.tournament_selection()
        assert selected.shape == (10, 5)

    def test_roulette_selection(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=10, gene_length=5)
        selected = ga.roulette_selection()
        assert selected.shape == (10, 5)

    def test_one_point_crossover(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=10, gene_length=5)
        c1, c2 = ga.one_point_crossover(np.ones(5), np.zeros(5))
        assert c1.shape == (5,)
        assert c2.shape == (5,)

    def test_two_point_crossover(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=10, gene_length=5)
        c1, c2 = ga.two_point_crossover(np.ones(5), np.zeros(5))
        assert c1.shape == (5,)
        assert c2.shape == (5,)

    def test_uniform_crossover(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=10, gene_length=5)
        c1, c2 = ga.uniform_crossover(np.ones(5), np.zeros(5))
        assert c1.shape == (5,)
        assert c2.shape == (5,)

    def test_bit_flip_mutation(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=10, gene_length=5, mutation_rate=0.5)
        original = np.ones(5)
        mutated = ga.bit_flip_mutation(original)
        assert mutated.shape == (5,)
        assert mutated.min() >= 0
        assert mutated.max() <= 1

    def test_gaussian_mutation(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=10, gene_length=5, mutation_rate=0.5)
        original = np.ones(5)
        mutated = ga.gaussian_mutation(original)
        assert mutated.shape == (5,)
        assert mutated.min() >= 0
        assert mutated.max() <= 1

    def test_swap_mutation(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=10, gene_length=5, mutation_rate=1.0)
        original = np.array([1, 2, 3, 4, 5])
        mutated = ga.swap_mutation(original)
        assert mutated.shape == (5,)

    def test_evolve_tournament(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=20, gene_length=5)
        best, fitness = ga.evolve(10)
        assert fitness <= 0
        assert ga.best_fitness_history[-1] == fitness

    def test_evolve_gaussian(self):
        ga = GeneticAlgorithm(self.fitness_fn, population_size=20, gene_length=5)
        best, fitness = ga.evolve(10, mutation_fn="gaussian")
        assert fitness <= 0
