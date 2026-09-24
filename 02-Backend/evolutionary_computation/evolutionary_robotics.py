import numpy as np


class EvolutionaryRobotics:
    def __init__(self, fitness_fn, genome_length, population_size, gene_bounds=(-1, 1), mutation_rate=0.1, crossover_rate=0.8):
        self.fitness_fn = fitness_fn
        self.genome_length = genome_length
        self.population_size = population_size
        self.gene_bounds = gene_bounds
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.population = np.random.uniform(gene_bounds[0], gene_bounds[1], (population_size, genome_length))
        self.best_fitness_history = []

    def evaluate(self):
        return np.array([self.fitness_fn(ind) for ind in self.population])

    def tournament_selection(self, tournament_size=3):
        selected = []
        for _ in range(self.population_size):
            indices = np.random.choice(self.population_size, tournament_size, replace=False)
            selected.append(self.population[indices[np.argmax(self.evaluate()[indices])]])
        return np.array(selected)

    def one_point_crossover(self, parent1, parent2):
        if np.random.rand() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        point = np.random.randint(1, self.genome_length)
        child1 = np.concatenate([parent1[:point], parent2[point:]])
        child2 = np.concatenate([parent2[:point], parent1[point:]])
        return child1, child2

    def gaussian_mutation(self, individual, sigma=0.1):
        individual = individual.copy()
        mask = np.random.rand(self.genome_length) < self.mutation_rate
        individual[mask] += np.random.normal(0, sigma, mask.sum())
        individual = np.clip(individual, self.gene_bounds[0], self.gene_bounds[1])
        return individual

    def evolve(self, generations):
        for gen in range(generations):
            fitness = self.evaluate()
            best_idx = np.argmax(fitness)
            self.best_fitness_history.append(fitness[best_idx])
            selected = self.tournament_selection()
            new_population = []
            for i in range(0, self.population_size, 2):
                p1, p2 = selected[i % self.population_size], selected[(i + 1) % self.population_size]
                c1, c2 = self.one_point_crossover(p1, p2)
                c1, c2 = self.gaussian_mutation(c1), self.gaussian_mutation(c2)
                new_population.extend([c1, c2])
            self.population = np.array(new_population[:self.population_size])
        fitness = self.evaluate()
        best_idx = np.argmax(fitness)
        return self.population[best_idx], fitness[best_idx]


class RobotController:
    def __init__(self, n_inputs, n_hidden, n_outputs):
        self.n_inputs = n_inputs
        self.n_hidden = n_hidden
        self.n_outputs = n_outputs
        self.w1 = np.random.randn(n_inputs, n_hidden) * 0.5
        self.b1 = np.random.randn(n_hidden) * 0.5
        self.w2 = np.random.randn(n_hidden, n_outputs) * 0.5
        self.b2 = np.random.randn(n_outputs) * 0.5

    def forward(self, x):
        x = np.dot(x, self.w1) + self.b1
        x = np.tanh(x)
        x = np.dot(x, self.w2) + self.b2
        return np.tanh(x)

    def get_genome(self):
        return np.concatenate([self.w1.flatten(), self.b1, self.w2.flatten(), self.b2])

    def get_genome_length(self):
        return np.prod(self.w1.shape) + np.prod(self.b1.shape) + np.prod(self.w2.shape) + np.prod(self.b2.shape)

    def set_genome(self, genome):
        offset = 0
        w1_shape = (self.n_inputs, self.n_hidden)
        w1_size = np.prod(w1_shape)
        self.w1 = genome[offset:offset + w1_size].reshape(w1_shape)
        offset += w1_size
        b1_size = self.n_hidden
        self.b1 = genome[offset:offset + b1_size]
        offset += b1_size
        w2_shape = (self.n_hidden, self.n_outputs)
        w2_size = np.prod(w2_shape)
        self.w2 = genome[offset:offset + w2_size].reshape(w2_shape)
        offset += w2_size
        b2_size = self.n_outputs
        self.b2 = genome[offset:offset + b2_size]
