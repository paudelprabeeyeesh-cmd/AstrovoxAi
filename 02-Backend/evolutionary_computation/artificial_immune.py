import numpy as np


class ArtificialImmuneSystem:
    def __init__(self, fitness_fn, population_size, n_dimensions, bounds, mutation_rate=0.1, n_clones=5):
        self.fitness_fn = fitness_fn
        self.population_size = population_size
        self.n_dimensions = n_dimensions
        self.bounds = bounds
        self.mutation_rate = mutation_rate
        self.n_clones = n_clones
        self.population = np.random.uniform(bounds[0], bounds[1], (population_size, n_dimensions))
        self.best_fitness_history = []

    def evaluate(self):
        return np.array([self.fitness_fn(ind) for ind in self.population])

    def affinity(self, individual):
        return self.fitness_fn(individual)

    def somatic_hypermutation(self, individual, affinity):
        mutation_strength = self.mutation_rate * max(0, (1 - affinity / (affinity + 1)))
        individual = individual + np.random.normal(0, mutation_strength, self.n_dimensions)
        individual = np.clip(individual, self.bounds[0], self.bounds[1])
        return individual

    def clonal_selection(self):
        fitness = self.evaluate()
        sorted_idx = np.argsort(fitness)[::-1]
        n_selected = max(1, self.population_size // 2)
        selected = self.population[sorted_idx[:n_selected]]
        clones = []
        for individual in selected:
            aff = self.affinity(individual)
            for _ in range(self.n_clones):
                clone = self.somatic_hypermutation(individual, aff)
                clones.append(clone)
        clones = np.array(clones)
        clone_fitness = np.array([self.fitness_fn(c) for c in clones])
        new_indices = np.argsort(clone_fitness)[-self.population_size:]
        return clones[new_indices]

    def negative_selection(self):
        fitness = self.evaluate()
        mean_fitness = fitness.mean()
        memory_set = self.population[fitness < mean_fitness].copy()
        self.population = np.vstack([self.population, memory_set])[:self.population_size]
        if len(self.population) < self.population_size:
            extra = np.random.uniform(self.bounds[0], self.bounds[1], (self.population_size - len(self.population), self.n_dimensions))
            self.population = np.vstack([self.population, extra])

    def evolve(self, generations):
        for gen in range(generations):
            fitness = self.evaluate()
            best_idx = np.argmax(fitness)
            self.best_fitness_history.append(fitness[best_idx])
            self.population = self.clonal_selection()
            self.negative_selection()
        fitness = self.evaluate()
        best_idx = np.argmax(fitness)
        return self.population[best_idx], fitness[best_idx]
