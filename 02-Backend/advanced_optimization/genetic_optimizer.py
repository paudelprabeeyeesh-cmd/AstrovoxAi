import copy
import random


def genetic_algorithm(f, bounds, pop_size=50, max_iter=100, mutation_rate=0.1, crossover_rate=0.7):
    dim = len(bounds)
    pop = [[random.uniform(b[0], b[1]) for b in bounds] for _ in range(pop_size)]

    for _ in range(max_iter):
        fitness = [f(ind) for ind in pop]
        idx_sorted = sorted(range(pop_size), key=lambda i: fitness[i])
        new_pop = []

        while len(new_pop) < pop_size:
            a, b = random.sample(idx_sorted[: pop_size // 2], 2)
            parent1 = pop[a]
            parent2 = pop[b]

            if random.random() < crossover_rate:
                point = random.randint(0, dim - 1)
                child1 = parent1[:point] + parent2[point:]
                child2 = parent2[:point] + parent1[point:]
            else:
                child1 = list(parent1)
                child2 = list(parent2)

            for child in (child1, child2):
                for i in range(dim):
                    if random.random() < mutation_rate:
                        child[i] = random.uniform(bounds[i][0], bounds[i][1])
                new_pop.append(child)
                if len(new_pop) == pop_size:
                    break

        pop = new_pop

    fitness = [f(ind) for ind in pop]
    best_idx = min(range(pop_size), key=lambda i: fitness[i])
    return pop[best_idx]
