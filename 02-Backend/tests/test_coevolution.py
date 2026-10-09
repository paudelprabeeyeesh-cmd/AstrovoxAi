import numpy as np
from evolutionary_computation.coevolution import CoevolutionaryGA, ArmsRace


class TestCoevolutionaryGA:
    def setup_method(self):
        self.fitness_fn = lambda ind, gen: -np.sum(ind ** 2)

    def test_init(self):
        ga = CoevolutionaryGA(self.fitness_fn, population_size=20, gene_length=5)
        assert ga.population.shape == (20, 5)

    def test_default_interaction(self):
        ga = CoevolutionaryGA(self.fitness_fn, population_size=20, gene_length=5)
        fitness = ga.default_interaction(np.ones(5), np.random.rand(20, 5))
        assert fitness > 0

    def test_evaluate(self):
        ga = CoevolutionaryGA(self.fitness_fn, population_size=10, gene_length=5)
        fitness = ga.evaluate()
        assert len(fitness) == 10

    def test_tournament_selection(self):
        ga = CoevolutionaryGA(self.fitness_fn, population_size=10, gene_length=5)
        selected = ga.tournament_selection()
        assert selected.shape == (10, 5)

    def test_one_point_crossover(self):
        ga = CoevolutionaryGA(self.fitness_fn, population_size=10, gene_length=5)
        c1, c2 = ga.one_point_crossover(np.ones(5), np.zeros(5))
        assert c1.shape == (5,)

    def test_gaussian_mutation(self):
        ga = CoevolutionaryGA(self.fitness_fn, population_size=10, gene_length=5, mutation_rate=0.5)
        ind = np.ones(5)
        mutated = ga.gaussian_mutation(ind)
        assert mutated.shape == (5,)

    def test_evolve(self):
        ga = CoevolutionaryGA(self.fitness_fn, population_size=20, gene_length=5)
        best, fitness = ga.evolve(10)
        assert fitness <= 0
        assert len(ga.best_fitness_history) == 10


class TestArmsRace:
    def setup_method(self):
        self.fitness_fn = lambda ind, gen: -np.sum(ind ** 2)

    def test_init(self):
        arms = ArmsRace(self.fitness_fn, population_size=20, gene_length=5)
        assert arms.attacker_population.shape == (10, 5)
        assert arms.defender_population.shape == (10, 5)

    def test_arms_race_interaction(self):
        arms = ArmsRace(self.fitness_fn, population_size=20, gene_length=5)
        interaction = arms.arms_race_interaction(np.ones(5), np.zeros(5))
        assert interaction > 0

    def test_attacker_fitness(self):
        arms = ArmsRace(self.fitness_fn, population_size=20, gene_length=5)
        fitness = arms.attacker_fitness(np.ones(5))
        assert isinstance(fitness, float)

    def test_defender_fitness(self):
        arms = ArmsRace(self.fitness_fn, population_size=20, gene_length=5)
        fitness = arms.defender_fitness(np.ones(5))
        assert isinstance(fitness, float)

    def test_evolve(self):
        arms = ArmsRace(self.fitness_fn, population_size=20, gene_length=5)
        result = arms.evolve(5)
        assert len(result) == 2
        assert len(arms.attack_history) == 5
