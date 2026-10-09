import numpy as np
from evolutionary_computation.ant_colony import AntColonyOptimizer, ContinuousAntColony


class TestAntColonyOptimizer:
    def setup_method(self):
        self.distances = [
            [0, 2, 9, 10],
            [1, 0, 6, 4],
            [15, 7, 0, 8],
            [6, 3, 12, 0]
        ]

    def test_init(self):
        aco = AntColonyOptimizer(self.distances, n_ants=10, n_iterations=5)
        assert aco.n_cities == 4

    def test_get_probability(self):
        aco = AntColonyOptimizer(self.distances, n_ants=10, n_iterations=5)
        prob = aco.get_probability(0, [1, 2, 3])
        assert prob.sum() > 0.99

    def test_construct_tour(self):
        aco = AntColonyOptimizer(self.distances, n_ants=10, n_iterations=5)
        tour = aco.construct_tour(0)
        assert len(tour) == 4

    def test_tour_distance(self):
        aco = AntColonyOptimizer(self.distances, n_ants=10, n_iterations=5)
        tour = [0, 1, 2, 3]
        dist = aco.tour_distance(tour)
        assert dist > 0

    def test_update_pheromone(self):
        aco = AntColonyOptimizer(self.distances, n_ants=10, n_iterations=5)
        aco.update_pheromone([[0, 1, 2, 3]], [10])
        assert aco.pheromone.min() >= 0

    def test_optimize(self):
        aco = AntColonyOptimizer(self.distances, n_ants=10, n_iterations=5)
        best_tour, best_dist = aco.optimize()
        assert len(best_tour) == 4
        assert best_dist > 0


class TestContinuousAntColony:
    def setup_method(self):
        self.fitness_fn = lambda x: -np.sum(x ** 2)

    def test_init(self):
        aco = ContinuousAntColony(self.fitness_fn, n_dimensions=5, bounds=(-1, 1), n_ants=10, n_iterations=5)
        assert aco.n_dimensions == 5

    def test_construct_solution(self):
        aco = ContinuousAntColony(self.fitness_fn, n_dimensions=5, bounds=(-1, 1), n_ants=10, n_iterations=5)
        sol = aco.construct_solution()
        assert len(sol) == 5

    def test_update_pheromone(self):
        aco = ContinuousAntColony(self.fitness_fn, n_dimensions=5, bounds=(-1, 1), n_ants=10, n_iterations=5)
        aco.update_pheromone([np.ones(5)], [1.0])
        assert aco.pheromone.min() >= 0

    def test_optimize(self):
        aco = ContinuousAntColony(self.fitness_fn, n_dimensions=5, bounds=(-1, 1), n_ants=10, n_iterations=5)
        best, fitness = aco.optimize()
        assert fitness <= 0
