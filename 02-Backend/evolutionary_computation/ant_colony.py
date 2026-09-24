import numpy as np


class AntColonyOptimizer:
    def __init__(self, distances, n_ants, n_iterations, alpha=1.0, beta=2.0, rho=0.5, Q=100.0):
        self.distances = np.array(distances, dtype=float)
        self.distances = np.where(self.distances == 0, np.inf, self.distances)
        np.fill_diagonal(self.distances, np.inf)
        self.n_cities = len(distances)
        self.n_ants = n_ants
        self.n_iterations = n_iterations
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.Q = Q
        self.pheromone = np.ones((self.n_cities, self.n_cities)) * 0.1
        self.best_tour = None
        self.best_distance = np.inf
        self.best_distance_history = []

    def get_probability(self, current, unvisited):
        pheromone = self.pheromone[current, unvisited] ** self.alpha
        visibility = (1.0 / self.distances[current, unvisited]) ** self.beta
        prob = pheromone * visibility
        return prob / prob.sum()

    def construct_tour(self, start_city):
        unvisited = list(range(self.n_cities))
        unvisited.remove(start_city)
        tour = [start_city]
        current = start_city
        while unvisited:
            prob = self.get_probability(current, unvisited)
            next_city = np.random.choice(unvisited, p=prob)
            tour.append(next_city)
            unvisited.remove(next_city)
            current = next_city
        return tour

    def tour_distance(self, tour):
        dist = 0
        for i in range(len(tour) - 1):
            dist += self.distances[tour[i], tour[i + 1]]
        dist += self.distances[tour[-1], tour[0]]
        return dist

    def update_pheromone(self, tours, distances):
        self.pheromone *= (1 - self.rho)
        for tour, dist in zip(tours, distances):
            if dist > 0 and np.isfinite(dist):
                for i in range(len(tour) - 1):
                    self.pheromone[tour[i], tour[i + 1]] += self.Q / dist
                    self.pheromone[tour[i + 1], tour[i]] += self.Q / dist

    def optimize(self):
        for iteration in range(self.n_iterations):
            tours = []
            tour_distances = []
            for ant in range(self.n_ants):
                start_city = np.random.randint(0, self.n_cities)
                tour = self.construct_tour(start_city)
                dist = self.tour_distance(tour)
                tours.append(tour)
                tour_distances.append(dist)
            best_idx = np.argmin(tour_distances)
            if tour_distances[best_idx] < self.best_distance:
                self.best_distance = tour_distances[best_idx]
                self.best_tour = tours[best_idx]
            self.best_distance_history.append(self.best_distance)
            self.update_pheromone(tours, tour_distances)
        return self.best_tour, self.best_distance


class ContinuousAntColony:
    def __init__(self, fitness_fn, n_dimensions, bounds, n_ants, n_iterations, alpha=1.0, beta=2.0, rho=0.5, Q=100.0):
        self.fitness_fn = fitness_fn
        self.n_dimensions = n_dimensions
        self.bounds = bounds
        self.n_ants = n_ants
        self.n_iterations = n_iterations
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.Q = Q
        self.pheromone = np.random.uniform(0, 1, n_dimensions) * 0.1
        self.best_solution = None
        self.best_fitness = -np.inf
        self.best_fitness_history = []

    def construct_solution(self):
        solution = np.zeros(self.n_dimensions)
        for j in range(self.n_dimensions):
            self.pheromone[j] ** self.alpha
            solution[j] = np.random.uniform(self.bounds[0], self.bounds[1], 1)[0]
        return solution

    def update_pheromone(self, solutions, fitnesses):
        self.pheromone *= (1 - self.rho)
        for sol, fit in zip(solutions, fitnesses):
            self.pheromone += self.Q * fit * sol

    def optimize(self):
        for iteration in range(self.n_iterations):
            solutions = [self.construct_solution() for _ in range(self.n_ants)]
            fitnesses = np.array([self.fitness_fn(sol) for sol in solutions])
            best_idx = np.argmax(fitnesses)
            if fitnesses[best_idx] > self.best_fitness:
                self.best_fitness = fitnesses[best_idx]
                self.best_solution = solutions[best_idx]
            self.best_fitness_history.append(self.best_fitness)
            self.update_pheromone(solutions, fitnesses)
        return self.best_solution, self.best_fitness
