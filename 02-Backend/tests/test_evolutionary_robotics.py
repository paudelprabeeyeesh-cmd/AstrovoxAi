import numpy as np
from evolutionary_computation.evolutionary_robotics import EvolutionaryRobotics, RobotController


class TestRobotController:
    def test_init(self):
        rc = RobotController(n_inputs=4, n_hidden=8, n_outputs=2)
        assert rc.n_inputs == 4
        assert rc.n_hidden == 8
        assert rc.n_outputs == 2

    def test_forward(self):
        rc = RobotController(n_inputs=4, n_hidden=8, n_outputs=2)
        x = np.random.randn(4)
        out = rc.forward(x)
        assert out.shape == (2,)

    def test_get_genome(self):
        rc = RobotController(n_inputs=4, n_hidden=8, n_outputs=2)
        genome = rc.get_genome()
        expected = 4 * 8 + 8 + 8 * 2 + 2
        assert len(genome) == expected

    def test_set_genome(self):
        rc = RobotController(n_inputs=4, n_hidden=8, n_outputs=2)
        genome = np.random.randn(rc.get_genome_length())
        rc.set_genome(genome)
        assert len(rc.get_genome()) == len(genome)


class TestEvolutionaryRobotics:
    def setup_method(self):
        self.fitness_fn = lambda x: -np.sum(x ** 2)

    def test_init(self):
        er = EvolutionaryRobotics(self.fitness_fn, genome_length=10, population_size=20)
        assert er.population.shape == (20, 10)

    def test_evaluate(self):
        er = EvolutionaryRobotics(self.fitness_fn, genome_length=10, population_size=10)
        fitness = er.evaluate()
        assert len(fitness) == 10

    def test_tournament_selection(self):
        er = EvolutionaryRobotics(self.fitness_fn, genome_length=10, population_size=10)
        selected = er.tournament_selection()
        assert selected.shape == (10, 10)

    def test_one_point_crossover(self):
        er = EvolutionaryRobotics(self.fitness_fn, genome_length=10, population_size=10)
        c1, c2 = er.one_point_crossover(np.ones(10), np.zeros(10))
        assert c1.shape == (10,)

    def test_gaussian_mutation(self):
        er = EvolutionaryRobotics(self.fitness_fn, genome_length=10, population_size=10, mutation_rate=0.5)
        ind = np.ones(10)
        mutated = er.gaussian_mutation(ind)
        assert mutated.shape == (10,)

    def test_evolve(self):
        er = EvolutionaryRobotics(self.fitness_fn, genome_length=10, population_size=20)
        best, fitness = er.evolve(10)
        assert fitness <= 0
        assert len(er.best_fitness_history) == 10
