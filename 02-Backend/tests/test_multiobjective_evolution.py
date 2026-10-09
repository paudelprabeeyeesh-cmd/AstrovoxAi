import numpy as np
from evolutionary_computation.multiobjective_evolution import NSGA2, SPEA2


class TestNSGA2:
    def setup_method(self):
        def fitness_fn(x):
            return np.array([np.sum((x - 1) ** 2), np.sum((x + 1) ** 2)])
        self.fitness_fn = fitness_fn

    def test_init(self):
        nsga = NSGA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2))
        assert nsga.population.shape == (20, 5)

    def test_evaluate(self):
        nsga = NSGA2(self.fitness_fn, population_size=10, n_dimensions=5, bounds=(-2, 2))
        fitness = nsga.evaluate()
        assert fitness.shape == (10, 2)

    def test_dominates(self):
        nsga = NSGA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2))
        assert nsga.dominates(np.array([3, 4]), np.array([1, 2]))
        assert not nsga.dominates(np.array([1, 2]), np.array([3, 4]))

    def test_non_dominated_sort(self):
        nsga = NSGA2(self.fitness_fn, population_size=10, n_dimensions=5, bounds=(-2, 2))
        fitness = nsga.evaluate()
        ranks, fronts = nsga.non_dominated_sort(fitness)
        assert len(ranks) == 10

    def test_crowding_distance(self):
        nsga = NSGA2(self.fitness_fn, population_size=10, n_dimensions=5, bounds=(-2, 2))
        fitness = nsga.evaluate()
        distance = nsga.crowding_distance(fitness, list(range(10)))
        assert len(distance) == 10

    def test_selection(self):
        nsga = NSGA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2))
        fitness = nsga.evaluate()
        selected, ranks = nsga.selection(fitness)
        assert len(selected) <= 20

    def test_crossover(self):
        nsga = NSGA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2))
        c1, c2 = nsga.crossover(np.ones(5), np.zeros(5))
        assert c1.shape == (5,)

    def test_mutate(self):
        nsga = NSGA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2), mutation_rate=0.5)
        ind = np.ones(5)
        mutated = nsga.mutate(ind)
        assert mutated.shape == (5,)

    def test_evolve(self):
        nsga = NSGA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2))
        solutions, fitnesses = nsga.evolve(10)
        assert solutions.shape[0] > 0
        assert fitnesses.shape[1] == 2
        assert len(nsga.best_fitness_history) == 10


class TestSPEA2:
    def setup_method(self):
        def fitness_fn(x):
            return np.array([np.sum((x - 1) ** 2), np.sum((x + 1) ** 2)])
        self.fitness_fn = fitness_fn

    def test_init(self):
        spea = SPEA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2))
        assert spea.population.shape == (20, 5)

    def test_evaluate(self):
        spea = SPEA2(self.fitness_fn, population_size=10, n_dimensions=5, bounds=(-2, 2))
        fitness = spea.evaluate()
        assert fitness.shape == (10, 2)

    def test_dominates(self):
        spea = SPEA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2))
        assert spea.dominates(np.array([3, 4]), np.array([1, 2]))
        assert not spea.dominates(np.array([1, 2]), np.array([3, 4]))

    def test_fitness_assignment(self):
        spea = SPEA2(self.fitness_fn, population_size=10, n_dimensions=5, bounds=(-2, 2))
        fitness = spea.evaluate()
        raw_fitness = spea.fitness_assignment(fitness)
        assert len(raw_fitness) == 10

    def test_environmental_selection(self):
        spea = SPEA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2))
        fitness = spea.evaluate()
        selected = spea.environmental_selection(fitness)
        assert len(selected) <= 20

    def test_evolve(self):
        spea = SPEA2(self.fitness_fn, population_size=20, n_dimensions=5, bounds=(-2, 2))
        solutions, fitnesses = spea.evolve(10)
        assert solutions.shape[0] > 0
        assert fitnesses.shape[1] == 2
        assert len(spea.best_fitness_history) == 10
