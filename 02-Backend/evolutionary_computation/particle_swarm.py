import numpy as np


class ParticleSwarmOptimizer:
    def __init__(self, fitness_fn, n_particles, n_dimensions, bounds, w=0.7, c1=2.0, c2=2.0):
        self.fitness_fn = fitness_fn
        self.n_particles = n_particles
        self.n_dimensions = n_dimensions
        self.bounds = bounds
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.positions = np.random.uniform(bounds[0], bounds[1], (n_particles, n_dimensions))
        self.velocities = np.random.uniform(-1, 1, (n_particles, n_dimensions))
        self.pbest = self.positions.copy()
        self.pbest_fitness = np.array([self.fitness_fn(p) for p in self.positions])
        self.gbest = self.positions[np.argmax(self.pbest_fitness)]
        self.gbest_fitness = np.max(self.pbest_fitness)
        self.best_fitness_history = [self.gbest_fitness]

    def update(self):
        r1, r2 = np.random.rand(self.n_particles, self.n_dimensions), np.random.rand(self.n_particles, self.n_dimensions)
        self.velocities = (self.w * self.velocities + self.c1 * r1 * (self.pbest - self.positions) + self.c2 * r2 * (self.gbest - self.positions))
        self.velocities = np.clip(self.velocities, -self.n_dimensions * 0.2, self.n_dimensions * 0.2)
        self.positions = self.positions + self.velocities
        self.positions = np.clip(self.positions, self.bounds[0], self.bounds[1])
        fitness = np.array([self.fitness_fn(p) for p in self.positions])
        for i in range(self.n_particles):
            if fitness[i] > self.pbest_fitness[i]:
                self.pbest[i] = self.positions[i].copy()
                self.pbest_fitness[i] = fitness[i]
                if fitness[i] > self.gbest_fitness:
                    self.gbest = self.positions[i].copy()
                    self.gbest_fitness = fitness[i]
        self.best_fitness_history.append(self.gbest_fitness)
        return fitness

    def optimize(self, n_iterations):
        for _ in range(n_iterations):
            self.update()
        return self.gbest, self.gbest_fitness


class QuantumPSO:
    def __init__(self, fitness_fn, n_particles, n_dimensions, bounds, theta=0.9, phi=2.0):
        self.fitness_fn = fitness_fn
        self.n_particles = n_particles
        self.n_dimensions = n_dimensions
        self.bounds = bounds
        self.theta = theta
        self.phi = phi
        self.positions = np.random.uniform(bounds[0], bounds[1], (n_particles, n_dimensions))
        self.gbest = self.positions[0]
        self.gbest_fitness = self.fitness_fn(self.gbest)
        self.best_fitness_history = [self.gbest_fitness]

    def update(self):
        delta = self.bounds[1] - self.bounds[0]
        for i in range(self.n_particles):
            if np.random.rand() < self.theta:
                self.positions[i] = self.positions[i] + self.phi * delta * (self.positions[i] - self.positions[i])
            else:
                self.positions[i] = self.positions[i] + self.phi * delta * (self.positions[i] - self.positions[i])
            self.positions[i] = np.clip(self.positions[i], self.bounds[0], self.bounds[1])
        fitness = np.array([self.fitness_fn(p) for p in self.positions])
        best_idx = np.argmax(fitness)
        if fitness[best_idx] > self.gbest_fitness:
            self.gbest = self.positions[best_idx].copy()
            self.gbest_fitness = fitness[best_idx]
        self.best_fitness_history.append(self.gbest_fitness)
        return fitness

    def optimize(self, n_iterations):
        for _ in range(n_iterations):
            self.update()
        return self.gbest, self.gbest_fitness
