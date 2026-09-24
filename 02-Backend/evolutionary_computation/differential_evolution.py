import numpy as np


class DifferentialEvolution:
    def __init__(self, fitness_fn, population_size, gene_length, gene_bounds=(0, 1), F=0.5, CR=0.9):
        self.fitness_fn = fitness_fn
        self.population_size = population_size
        self.gene_length = gene_length
        self.gene_bounds = gene_bounds
        self.F = F
        self.CR = CR
        self.population = np.random.uniform(gene_bounds[0], gene_bounds[1], (population_size, gene_length))
        self.best_fitness_history = []

    def evaluate(self):
        return np.array([self.fitness_fn(ind) for ind in self.population])

    def rand1_mutation(self, target_idx):
        candidates = np.random.choice([i for i in range(self.population_size) if i != target_idx], 3, replace=False)
        a, b, c = self.population[candidates]
        mutant = a + self.F * (b - c)
        return np.clip(mutant, self.gene_bounds[0], self.gene_bounds[1])

    def best1_mutation(self, target_idx):
        best_idx = np.argmax(self.evaluate())
        candidates = np.random.choice([i for i in range(self.population_size) if i != target_idx and i != best_idx], 2, replace=False)
        b, c = self.population[candidates]
        mutant = self.population[best_idx] + self.F * (b - c)
        return np.clip(mutant, self.gene_bounds[0], self.gene_bounds[1])

    def current_to_best1_mutation(self, target_idx):
        best_idx = np.argmax(self.evaluate())
        candidate = np.random.choice([i for i in range(self.population_size) if i != target_idx])
        mutant = self.population[target_idx] + self.F * (self.population[best_idx] - self.population[target_idx]) + self.F * (self.population[candidate] - self.population[candidate])
        return np.clip(mutant, self.gene_bounds[0], self.gene_bounds[1])

    def crossover(self, target, mutant):
        j_rand = np.random.randint(self.gene_length)
        mask = np.random.rand(self.gene_length) < self.CR
        mask[j_rand] = True
        trial = np.where(mask, mutant, target)
        return trial

    def evolve(self, generations, mutation_fn="rand1"):
        for gen in range(generations):
            fitness = self.evaluate()
            best_idx = np.argmax(fitness)
            self.best_fitness_history.append(fitness[best_idx])
            new_population = []
            for i in range(self.population_size):
                if mutation_fn == "rand1":
                    mutant = self.rand1_mutation(i)
                elif mutation_fn == "best1":
                    mutant = self.best1_mutation(i)
                else:
                    mutant = self.current_to_best1_mutation(i)
                trial = self.crossover(self.population[i], mutant)
                trial = np.clip(trial, self.gene_bounds[0], self.gene_bounds[1])
                trial_fitness = self.fitness_fn(trial)
                if trial_fitness > fitness[i]:
                    new_population.append(trial)
                else:
                    new_population.append(self.population[i])
            self.population = np.array(new_population)
        fitness = self.evaluate()
        best_idx = np.argmax(fitness)
        return self.population[best_idx], fitness[best_idx]
