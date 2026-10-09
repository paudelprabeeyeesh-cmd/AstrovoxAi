import numpy as np


class CoevolutionaryGA:
    def __init__(self, fitness_fn, population_size, gene_length, gene_bounds=(0, 1), mutation_rate=0.01, crossover_rate=0.8, interaction_fn=None):
        self.fitness_fn = fitness_fn
        self.population_size = population_size
        self.gene_length = gene_length
        self.gene_bounds = gene_bounds
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.interaction_fn = interaction_fn if interaction_fn else self.default_interaction
        self.population = np.random.uniform(gene_bounds[0], gene_bounds[1], (population_size, gene_length))
        self.best_fitness_history = []

    def default_interaction(self, individual, population):
        return np.array([np.linalg.norm(individual - ind) for ind in population]).mean()

    def evaluate(self, generation=0):
        fitness = np.array([self.fitness_fn(ind, generation) for ind in self.population])
        interaction_fitness = np.array([self.interaction_fn(ind, self.population) for ind in self.population])
        return fitness + 0.3 * interaction_fitness

    def tournament_selection(self, tournament_size=3):
        selected = []
        for _ in range(self.population_size):
            indices = np.random.choice(self.population_size, tournament_size, replace=False)
            selected.append(self.population[indices[np.argmax(self.evaluate()[indices])]])
        return np.array(selected)

    def one_point_crossover(self, parent1, parent2):
        if np.random.rand() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        point = np.random.randint(1, self.gene_length)
        child1 = np.concatenate([parent1[:point], parent2[point:]])
        child2 = np.concatenate([parent2[:point], parent1[point:]])
        return child1, child2

    def gaussian_mutation(self, individual, sigma=0.1):
        individual = individual.copy()
        mask = np.random.rand(self.gene_length) < self.mutation_rate
        individual[mask] += np.random.normal(0, sigma, mask.sum())
        individual = np.clip(individual, self.gene_bounds[0], self.gene_bounds[1])
        return individual

    def evolve(self, generations):
        for gen in range(generations):
            fitness = self.evaluate(gen)
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


class ArmsRace(CoevolutionaryGA):
    def __init__(self, fitness_fn, population_size, gene_length, gene_bounds=(0, 1)):
        super().__init__(fitness_fn, population_size, gene_length, gene_bounds, interaction_fn=self.arms_race_interaction)
        self.attacker_population = np.random.uniform(gene_bounds[0], gene_bounds[1], (population_size // 2, gene_length))
        self.defender_population = np.random.uniform(gene_bounds[0], gene_bounds[1], (population_size // 2, gene_length))
        self.attack_history = []
        self.defense_history = []

    def arms_race_interaction(self, attacker, defender):
        return np.linalg.norm(attacker - defender) / (self.gene_length ** 0.5)

    def attacker_fitness(self, attacker, generation=0):
        fitnesses = []
        for defender in self.defender_population:
            fitnesses.append(self.arms_race_interaction(attacker, defender))
        return np.mean(fitnesses)

    def defender_fitness(self, defender, generation=0):
        fitnesses = []
        for attacker in self.attacker_population:
            fitnesses.append(1 - self.arms_race_interaction(attacker, defender))
        return np.mean(fitnesses)

    def evolve(self, generations):
        for gen in range(generations):
            attack_fitness = np.array([self.attacker_fitness(a, gen) for a in self.attacker_population])
            defense_fitness = np.array([self.defender_fitness(d, gen) for d in self.defender_population])
            self.attack_history.append(np.mean(attack_fitness))
            self.defense_history.append(np.mean(defense_fitness))
            n_selected = max(1, self.population_size // 4)
            attacker_candidates = self.attacker_population[np.argsort(attack_fitness)[-n_selected:]]
            defender_candidates = self.defender_population[np.argsort(defense_fitness)[-n_selected:]]
            new_attackers = [self.gaussian_mutation(ind, sigma=0.05) for ind in attacker_candidates]
            new_defenders = [self.gaussian_mutation(ind, sigma=0.05) for ind in defender_candidates]
            while len(new_attackers) < self.population_size // 2:
                new_attackers.append(np.random.uniform(self.gene_bounds[0], self.gene_bounds[1], self.gene_length))
            while len(new_defenders) < self.population_size // 2:
                new_defenders.append(np.random.uniform(self.gene_bounds[0], self.gene_bounds[1], self.gene_length))
            self.attacker_population = np.array(new_attackers[:self.population_size // 2])
            self.defender_population = np.array(new_defenders[:self.population_size // 2])
        return self.attacker_population[0], self.defender_population[0]
