import numpy as np


class EvolutionStrategy:
    def __init__(self, fitness_fn, mu, lambda_, gene_length, mutation_rate=0.1, gene_bounds=(0, 1), tau=None, tau_prime=None):
        self.fitness_fn = fitness_fn
        self.mu = mu
        self.lambda_ = lambda_
        self.gene_length = gene_length
        self.mutation_rate = mutation_rate
        self.gene_bounds = gene_bounds
        self.population = np.random.uniform(gene_bounds[0], gene_bounds[1], (mu, gene_length))
        self.sigma = np.full((mu, gene_length), mutation_rate)
        self.tau = tau if tau else 1.0 / np.sqrt(2.0 * gene_length)
        self.tau_prime = tau_prime if tau_prime else 1.0 / np.sqrt(2.0 * np.sqrt(gene_length))
        self.best_fitness_history = []

    def evaluate(self, individuals):
        return np.array([self.fitness_fn(ind) for ind in individuals])

    def self_adaptive_mutation(self, individual, sigma):
        sigma = np.abs(sigma)
        noise = self.tau_prime * np.random.randn() + self.tau * np.random.randn(self.gene_length)
        sigma = sigma * np.exp(noise)
        sigma = np.clip(sigma, 1e-6, 0.5)
        individual = individual + sigma * np.random.randn(self.gene_length)
        individual = np.clip(individual, self.gene_bounds[0], self.gene_bounds[1])
        return individual, sigma

    def recombine(self, parents):
        parent_idx = np.random.choice(self.mu, self.lambda_, replace=True)
        offspring = []
        for idx in parent_idx:
            p_idx = np.random.choice(self.mu, 2, replace=False)
            offspring.append((self.population[p_idx[0]] + self.population[p_idx[1]]) / 2.0)
        return np.array(offspring)

    def evolve(self, generations):
        for gen in range(generations):
            fitness = self.evaluate(self.population)
            best_idx = np.argmax(fitness)
            self.best_fitness_history.append(fitness[best_idx])
            parent_idx = np.argsort(fitness)[-self.mu:]
            parents = self.population[parent_idx]
            parent_sigma = self.sigma[parent_idx]
            offspring = self.recombine(parents)
            offspring_sigma = np.repeat(parent_sigma, self.lambda_ // self.mu, axis=0)[:self.lambda_]
            if offspring_sigma.shape[0] < self.lambda_:
                offspring_sigma = np.repeat(offspring_sigma, (self.lambda_ + offspring_sigma.shape[0] - 1) // offspring_sigma.shape[0], axis=0)[:self.lambda_]
            new_individuals = []
            new_sigma = []
            for ind, sig in zip(offspring, offspring_sigma):
                mut_ind, mut_sig = self.self_adaptive_mutation(ind, sig)
                new_individuals.append(mut_ind)
                new_sigma.append(mut_sig)
            new_individuals = np.array(new_individuals)
            new_sigma = np.array(new_sigma)
            all_ind = np.vstack([self.population, new_individuals])
            all_sig = np.vstack([self.sigma, new_sigma])
            all_fitness = self.evaluate(all_ind)
            best_idx = np.argsort(all_fitness)[-self.mu:]
            self.population = all_ind[best_idx]
            self.sigma = all_sig[best_idx]
        fitness = self.evaluate(self.population)
        best_idx = np.argmax(fitness)
        return self.population[best_idx], fitness[best_idx]
