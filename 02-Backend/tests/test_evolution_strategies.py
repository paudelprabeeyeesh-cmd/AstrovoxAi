import numpy as np
from evolutionary_computation.evolution_strategies import EvolutionStrategy


class TestEvolutionStrategy:
    def setup_method(self):
        self.fitness_fn = lambda x: -np.sum(x ** 2)

    def test_init(self):
        es = EvolutionStrategy(self.fitness_fn, mu=10, lambda_=30, gene_length=5)
        assert es.population.shape == (10, 5)

    def test_evaluate(self):
        es = EvolutionStrategy(self.fitness_fn, mu=10, lambda_=30, gene_length=5)
        fitness = es.evaluate(es.population)
        assert len(fitness) == 10

    def test_self_adaptive_mutation(self):
        es = EvolutionStrategy(self.fitness_fn, mu=10, lambda_=30, gene_length=5)
        ind = np.ones(5)
        sig = np.full(5, 0.1)
        mut_ind, mut_sig = es.self_adaptive_mutation(ind, sig)
        assert mut_ind.shape == (5,)
        assert mut_sig.shape == (5,)
        assert np.all(mut_sig > 0)

    def test_recombine(self):
        es = EvolutionStrategy(self.fitness_fn, mu=10, lambda_=30, gene_length=5)
        offspring = es.recombine(es.population)
        assert offspring.shape == (30, 5)

    def test_evolve(self):
        es = EvolutionStrategy(self.fitness_fn, mu=10, lambda_=30, gene_length=5)
        best, fitness = es.evolve(10)
        assert fitness <= 0
        assert es.best_fitness_history[-1] == fitness
