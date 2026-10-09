import numpy as np


class NeuralNetwork:
    def __init__(self, layer_sizes):
        self.layer_sizes = layer_sizes
        self.weights = []
        self.biases = []
        for i in range(len(layer_sizes) - 1):
            self.weights.append(np.random.randn(layer_sizes[i], layer_sizes[i + 1]) * 0.1)
            self.biases.append(np.random.randn(layer_sizes[i + 1]) * 0.1)

    def forward(self, x):
        for w, b in zip(self.weights, self.biases):
            x = np.dot(x, w) + b
            x = np.tanh(x)
        return x

    def get_genome(self):
        genome = []
        for w, b in zip(self.weights, self.biases):
            genome.extend(w.flatten())
            genome.extend(b.flatten())
        return np.array(genome)

    def set_genome(self, genome):
        offset = 0
        for i in range(len(self.layer_sizes) - 1):
            w_shape = (self.layer_sizes[i], self.layer_sizes[i + 1])
            w_size = np.prod(w_shape)
            self.weights[i] = genome[offset:offset + w_size].reshape(w_shape)
            offset += w_size
            b_size = self.layer_sizes[i + 1]
            self.biases[i] = genome[offset:offset + b_size]
            offset += b_size

    def get_genome_length(self):
        return sum(np.prod(w.shape) + np.prod(b.shape) for w, b in zip(self.weights, self.biases))


class Neuroevolution:
    def __init__(self, fitness_fn, layer_sizes, population_size=50, mutation_rate=0.1, crossover_rate=0.7):
        self.fitness_fn = fitness_fn
        self.layer_sizes = layer_sizes
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.genome_length = NeuralNetwork(layer_sizes).get_genome_length()
        self.population = np.random.uniform(-1, 1, (population_size, self.genome_length))
        self.best_fitness_history = []

    def evaluate(self):
        fitnesses = []
        for genome in self.population:
            net = NeuralNetwork(self.layer_sizes)
            net.set_genome(genome)
            fitnesses.append(self.fitness_fn(net))
        return np.array(fitnesses)

    def tournament_selection(self, tournament_size=3):
        selected = []
        for _ in range(self.population_size):
            indices = np.random.choice(self.population_size, tournament_size, replace=False)
            selected.append(self.population[indices[np.argmax(self.evaluate()[indices])]])
        return np.array(selected)

    def crossover(self, parent1, parent2):
        if np.random.rand() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        mask = np.random.rand(self.genome_length) > 0.5
        child1 = np.where(mask, parent1, parent2)
        child2 = np.where(mask, parent2, parent1)
        return child1, child2

    def mutate(self, individual):
        mask = np.random.rand(self.genome_length) < self.mutation_rate
        individual = individual.copy()
        individual[mask] += np.random.normal(0, 0.1, mask.sum())
        individual = np.clip(individual, -1, 1)
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
                c1, c2 = self.crossover(p1, p2)
                c1, c2 = self.mutate(c1), self.mutate(c2)
                new_population.extend([c1, c2])
            self.population = np.array(new_population[:self.population_size])
        fitness = self.evaluate()
        best_idx = np.argmax(fitness)
        return self.population[best_idx], fitness[best_idx]


class TopologyOptimizer:
    def __init__(self, fitness_fn, min_nodes=2, max_nodes=10, population_size=30):
        self.fitness_fn = fitness_fn
        self.min_nodes = min_nodes
        self.max_nodes = max_nodes
        self.population_size = population_size
        self.population = [self.random_genome() for _ in range(population_size)]
        self.best_fitness_history = []

    def random_genome(self):
        n_nodes = np.random.randint(self.min_nodes, self.max_nodes + 1)
        connections = []
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                if np.random.rand() > 0.5:
                    connections.append((i, j))
        return n_nodes, connections

    def decode(self, genome):
        n_nodes, connections = genome
        return n_nodes, connections

    def evolve(self, generations):
        for gen in range(generations):
            fitness = np.array([self.fitness_fn(self.decode(g)) for g in self.population])
            best_idx = np.argmax(fitness)
            self.best_fitness_history.append(fitness[best_idx])
            sorted_idx = np.argsort(fitness)[::-1]
            survivors = [self.population[i] for i in sorted_idx[:max(1, self.population_size // 2)]]
            offspring = []
            while len(offspring) < self.population_size - len(survivors):
                parent = survivors[np.random.randint(len(survivors))]
                child = list(parent)
                if np.random.rand() < 0.3:
                    n_nodes = child[0]
                    connections = child[1]
                    if np.random.rand() < 0.5:
                        n_nodes = max(self.min_nodes, n_nodes - 1)
                    else:
                        n_nodes = min(self.max_nodes, n_nodes + 1)
                    child = (n_nodes, connections)
                offspring.append(tuple(child))
            self.population = survivors + offspring[:self.population_size - len(survivors)]
        fitness = np.array([self.fitness_fn(self.decode(g)) for g in self.population])
        best_idx = np.argmax(fitness)
        return self.population[best_idx], fitness[best_idx]
