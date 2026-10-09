import numpy as np


class GeneticAlgorithm:
    def __init__(self, fitness_fn, population_size, gene_length, mutation_rate=0.01, crossover_rate=0.8, gene_bounds=(0, 1)):
        self.fitness_fn = fitness_fn
        self.population_size = population_size
        self.gene_length = gene_length
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.gene_bounds = gene_bounds
        self.population = np.random.uniform(gene_bounds[0], gene_bounds[1], (population_size, gene_length))
        self.best_fitness_history = []

    def evaluate(self):
        return np.array([self.fitness_fn(ind) for ind in self.population])

    def tournament_selection(self, tournament_size=3):
        selected = []
        for _ in range(self.population_size):
            indices = np.random.choice(self.population_size, tournament_size, replace=False)
            selected.append(self.population[indices[np.argmax(self.evaluate()[indices])]])
        return np.array(selected)

    def roulette_selection(self):
        fitness = self.evaluate()
        fitness = fitness - fitness.min() + 1e-6
        probs = fitness / fitness.sum()
        indices = np.random.choice(self.population_size, self.population_size, p=probs)
        return self.population[indices]

    def one_point_crossover(self, parent1, parent2):
        if np.random.rand() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        point = np.random.randint(1, self.gene_length)
        child1 = np.concatenate([parent1[:point], parent2[point:]])
        child2 = np.concatenate([parent2[:point], parent1[point:]])
        return child1, child2

    def two_point_crossover(self, parent1, parent2):
        if np.random.rand() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        p1, p2 = np.random.choice(range(1, self.gene_length), 2, replace=False)
        p1, p2 = sorted([p1, p2])
        child1 = np.concatenate([parent1[:p1], parent2[p1:p2], parent1[p2:]])
        child2 = np.concatenate([parent2[:p1], parent1[p1:p2], parent2[p2:]])
        return child1, child2

    def uniform_crossover(self, parent1, parent2):
        if np.random.rand() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        mask = np.random.rand(self.gene_length) > 0.5
        child1 = np.where(mask, parent1, parent2)
        child2 = np.where(mask, parent2, parent1)
        return child1, child2

    def bit_flip_mutation(self, individual):
        mask = np.random.rand(self.gene_length) < self.mutation_rate
        individual = individual.copy()
        individual[mask] = np.random.uniform(self.gene_bounds[0], self.gene_bounds[1], mask.sum())
        return individual

    def gaussian_mutation(self, individual, sigma=0.1):
        individual = individual.copy()
        mask = np.random.rand(self.gene_length) < self.mutation_rate
        individual[mask] += np.random.normal(0, sigma, mask.sum())
        individual = np.clip(individual, self.gene_bounds[0], self.gene_bounds[1])
        return individual

    def swap_mutation(self, individual):
        individual = individual.copy()
        if np.random.rand() < self.mutation_rate:
            i, j = np.random.choice(self.gene_length, 2, replace=False)
            individual[i], individual[j] = individual[j], individual[i]
        return individual

    def evolve(self, generations, selection_fn="tournament", crossover_fn="two_point", mutation_fn="gaussian"):
        for gen in range(generations):
            fitness = self.evaluate()
            best_idx = np.argmax(fitness)
            self.best_fitness_history.append(fitness[best_idx])
            if selection_fn == "tournament":
                selected = self.tournament_selection()
            elif selection_fn == "roulette":
                selected = self.roulette_selection()
            else:
                selected = self.tournament_selection()
            new_population = []
            for i in range(0, self.population_size, 2):
                p1, p2 = selected[i % self.population_size], selected[(i + 1) % self.population_size]
                if crossover_fn == "one_point":
                    c1, c2 = self.one_point_crossover(p1, p2)
                elif crossover_fn == "uniform":
                    c1, c2 = self.uniform_crossover(p1, p2)
                else:
                    c1, c2 = self.two_point_crossover(p1, p2)
                if mutation_fn == "bit_flip":
                    c1, c2 = self.bit_flip_mutation(c1), self.bit_flip_mutation(c2)
                elif mutation_fn == "gaussian":
                    c1, c2 = self.gaussian_mutation(c1), self.gaussian_mutation(c2)
                elif mutation_fn == "swap":
                    c1, c2 = self.swap_mutation(c1), self.swap_mutation(c2)
                else:
                    c1, c2 = self.gaussian_mutation(c1), self.gaussian_mutation(c2)
                new_population.extend([c1, c2])
            self.population = np.array(new_population[:self.population_size])
        fitness = self.evaluate()
        best_idx = np.argmax(fitness)
        return self.population[best_idx], fitness[best_idx]
