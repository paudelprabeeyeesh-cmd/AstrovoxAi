import numpy as np
from evolutionary_computation.neural_evolution import NeuralNetwork, Neuroevolution, TopologyOptimizer


class TestNeuralNetwork:
    def test_init(self):
        net = NeuralNetwork([2, 4, 1])
        assert net.layer_sizes == [2, 4, 1]

    def test_forward(self):
        net = NeuralNetwork([2, 4, 1])
        x = np.array([1.0, 2.0])
        out = net.forward(x)
        assert out.shape == (1,)

    def test_get_genome(self):
        net = NeuralNetwork([2, 4, 1])
        genome = net.get_genome()
        expected = 2 * 4 + 4 + 4 * 1 + 1
        assert len(genome) == expected

    def test_set_genome(self):
        net = NeuralNetwork([2, 4, 1])
        genome = np.random.randn(net.get_genome_length())
        net.set_genome(genome)
        assert len(net.get_genome()) == len(genome)

    def test_get_genome_length(self):
        net = NeuralNetwork([2, 4, 1])
        assert net.get_genome_length() > 0


class TestNeuroevolution:
    def setup_method(self):
        self.fitness_fn = lambda net: -np.sum(net.forward(np.array([[1.0, 2.0]])) ** 2)

    def test_init(self):
        ne = Neuroevolution(self.fitness_fn, [2, 4, 1])
        assert ne.population.shape[1] == 17

    def test_evaluate(self):
        ne = Neuroevolution(self.fitness_fn, [2, 4, 1], population_size=5)
        fitness = ne.evaluate()
        assert len(fitness) == 5

    def test_tournament_selection(self):
        ne = Neuroevolution(self.fitness_fn, [2, 4, 1], population_size=10)
        selected = ne.tournament_selection()
        assert selected.shape == (10, ne.genome_length)

    def test_crossover(self):
        ne = Neuroevolution(self.fitness_fn, [2, 4, 1], population_size=10)
        c1, c2 = ne.crossover(np.ones(ne.genome_length), np.zeros(ne.genome_length))
        assert c1.shape == (ne.genome_length,)
        assert c2.shape == (ne.genome_length,)

    def test_mutate(self):
        ne = Neuroevolution(self.fitness_fn, [2, 4, 1], population_size=10, mutation_rate=0.5)
        ind = np.ones(ne.genome_length)
        mutated = ne.mutate(ind)
        assert mutated.shape == ind.shape

    def test_evolve(self):
        ne = Neuroevolution(self.fitness_fn, [2, 4, 1], population_size=10)
        best, fitness = ne.evolve(5)
        assert fitness <= 0
        assert len(ne.best_fitness_history) == 5


class TestTopologyOptimizer:
    def setup_method(self):
        self.fitness_fn = lambda genome: -np.sum(np.array([genome[0]]) ** 2)

    def test_init(self):
        to = TopologyOptimizer(self.fitness_fn)
        assert len(to.population) > 0

    def test_random_genome(self):
        to = TopologyOptimizer(self.fitness_fn)
        genome = to.random_genome()
        assert genome[0] >= to.min_nodes
        assert genome[0] <= to.max_nodes

    def test_decode(self):
        to = TopologyOptimizer(self.fitness_fn)
        genome = to.random_genome()
        n_nodes, connections = to.decode(genome)
        assert n_nodes >= to.min_nodes

    def test_evolve(self):
        to = TopologyOptimizer(self.fitness_fn, population_size=10)
        best, fitness = to.evolve(5)
        assert fitness <= 0
        assert len(to.best_fitness_history) == 5
