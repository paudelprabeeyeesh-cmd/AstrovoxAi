import numpy as np


class NSGA2:
    def __init__(self, fitness_fn, population_size, n_dimensions, bounds, mutation_rate=0.1, crossover_rate=0.9):
        self.fitness_fn = fitness_fn
        self.population_size = population_size
        self.n_dimensions = n_dimensions
        self.bounds = bounds
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.population = np.random.uniform(bounds[0], bounds[1], (population_size, n_dimensions))
        self.best_fitness_history = []

    def evaluate(self):
        return np.array([self.fitness_fn(ind) for ind in self.population])

    def non_dominated_sort(self, fitness):
        n_solutions = len(fitness)
        ranks = np.zeros(n_solutions)
        dominated = [set() for _ in range(n_solutions)]
        domination_counts = np.zeros(n_solutions)
        fronts = []
        for i in range(n_solutions):
            for j in range(n_solutions):
                if i == j:
                    continue
                if self.dominates(fitness[i], fitness[j]):
                    dominated[i].add(j)
                elif self.dominates(fitness[j], fitness[i]):
                    domination_counts[i] += 1
            if domination_counts[i] == 0:
                ranks[i] = 0
                fronts.append({i})
        for front in fronts:
            next_front = set()
            for i in front:
                for j in dominated[i]:
                    domination_counts[j] -= 1
                    if domination_counts[j] == 0:
                        ranks[j] = ranks[list(fronts[0])[0]] + 1 if fronts else 1
                        next_front.add(j)
            if next_front:
                fronts.append(next_front)
        return ranks, fronts

    def dominates(self, fitness1, fitness2):
        return np.all(fitness1 >= fitness2) and np.any(fitness1 > fitness2)

    def crowding_distance(self, fitness, front):
        if len(front) <= 2:
            return np.array([np.inf if i in front else 0 for i in range(len(fitness))])
        distance = np.zeros(len(fitness))
        for m in range(fitness.shape[1]):
            sorted_front = sorted(front, key=lambda i: fitness[i, m])
            distance[sorted_front[0]] = np.inf
            distance[sorted_front[-1]] = np.inf
            for i in range(1, len(sorted_front) - 1):
                distance[sorted_front[i]] = (fitness[sorted_front[i + 1], m] - fitness[sorted_front[i - 1], m]) / (fitness[:, m].max() - fitness[:, m].min() + 1e-6)
        return distance

    def selection(self, fitness):
        ranks, fronts = self.non_dominated_sort(fitness)
        distance = self.crowding_distance(fitness, range(len(fitness)))
        selected = []
        for front in fronts:
            if len(selected) + len(front) <= self.population_size:
                selected.extend(front)
            else:
                front_distance = [(i, distance[i]) for i in front]
                front_distance.sort(key=lambda x: x[1], reverse=True)
                selected.extend([x[0] for x in front_distance[:self.population_size - len(selected)]])
        return np.array(selected), ranks

    def crossover(self, parent1, parent2):
        if np.random.rand() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        point = np.random.randint(1, self.n_dimensions)
        child1 = np.concatenate([parent1[:point], parent2[point:]])
        child2 = np.concatenate([parent2[:point], parent1[point:]])
        return child1, child2

    def mutate(self, individual):
        mask = np.random.rand(self.n_dimensions) < self.mutation_rate
        individual = individual.copy()
        individual[mask] += np.random.normal(0, 0.1, mask.sum())
        individual = np.clip(individual, self.bounds[0], self.bounds[1])
        return individual

    def evolve(self, generations):
        for gen in range(generations):
            fitness = self.evaluate()
            selected, ranks = self.selection(fitness)
            best_idx = np.argmax(fitness[:, 0])
            self.best_fitness_history.append(fitness[best_idx])
            new_population = []
            for i in range(0, len(selected), 2):
                p1, p2 = self.population[selected[i % len(selected)]], self.population[selected[(i + 1) % len(selected)]]
                c1, c2 = self.crossover(p1, p2)
                c1, c2 = self.mutate(c1), self.mutate(c2)
                new_population.extend([c1, c2])
            self.population = np.array(new_population[:self.population_size])
        fitness = self.evaluate()
        selected, ranks = self.selection(fitness)
        return self.population[selected], fitness[selected]


class SPEA2:
    def __init__(self, fitness_fn, population_size, n_dimensions, bounds, mutation_rate=0.1, crossover_rate=0.9):
        self.fitness_fn = fitness_fn
        self.population_size = population_size
        self.n_dimensions = n_dimensions
        self.bounds = bounds
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.population = np.random.uniform(bounds[0], bounds[1], (population_size, n_dimensions))
        self.best_fitness_history = []

    def evaluate(self):
        return np.array([self.fitness_fn(ind) for ind in self.population])

    def fitness_assignment(self, fitness):
        n = len(fitness)
        strength = np.zeros(n)
        for i in range(n):
            for j in range(n):
                if self.dominates(fitness[i], fitness[j]):
                    strength[i] += 1
        raw_fitness = np.zeros(n)
        for i in range(n):
            for j in range(n):
                if self.dominates(fitness[j], fitness[i]):
                    raw_fitness[i] += strength[j]
        return raw_fitness

    def dominates(self, fitness1, fitness2):
        return np.all(fitness1 >= fitness2) and np.any(fitness1 > fitness2)

    def environmental_selection(self, fitness):
        raw_fitness = self.fitness_assignment(fitness)
        sorted_idx = np.argsort(raw_fitness)
        selected = []
        for idx in sorted_idx:
            if len(selected) < self.population_size:
                selected.append(idx)
        if len(selected) < self.population_size:
            remaining = [i for i in range(len(fitness)) if i not in selected]
            selected.extend(remaining[:self.population_size - len(selected)])
        return np.array(selected)

    def evolve(self, generations):
        for gen in range(generations):
            fitness = self.evaluate()
            selected = self.environmental_selection(fitness)
            best_idx = np.argmax(fitness[:, 0])
            self.best_fitness_history.append(fitness[best_idx])
            self.population = self.population[selected]
            if len(self.population) < self.population_size:
                extra = np.random.uniform(self.bounds[0], self.bounds[1], (self.population_size - len(self.population), self.n_dimensions))
                self.population = np.vstack([self.population, extra])
        fitness = self.evaluate()
        selected = self.environmental_selection(fitness)
        return self.population[selected], fitness[selected]
