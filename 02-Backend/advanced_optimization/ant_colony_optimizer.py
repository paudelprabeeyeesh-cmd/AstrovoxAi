import copy
import math
import random


def ant_colony_optimization(f, bounds, n_ants=20, max_iter=100, alpha=1.0, beta=2.0, rho=0.5, Q=1.0):
    dim = len(bounds)
    archive = [[random.uniform(b[0], b[1]) for b in bounds] for _ in range(n_ants)]
    archive_fitness = [f(sol) for sol in archive]

    best = copy.deepcopy(archive[0])
    best_val = archive_fitness[0]

    for _ in range(max_iter):
        for i in range(len(archive)):
            if archive_fitness[i] < best_val:
                best = copy.deepcopy(archive[i])
                best_val = archive_fitness[i]

        new_archive = []
        for _ in range(n_ants):
            weights = [math.exp(-archive_fitness[i]) for i in range(len(archive))]
            total = sum(weights)
            if total == 0:
                guide = random.choice(archive)
            else:
                r = random.uniform(0, total)
                cumsum = 0.0
                guide_idx = 0
                for i, w in enumerate(weights):
                    cumsum += w
                    if cumsum >= r:
                        guide_idx = i
                        break
                guide = archive[guide_idx]

            scale = 0.5 * (1 - _ / max_iter) + 0.01
            ant = [guide[j] + random.gauss(0, scale * (bounds[j][1] - bounds[j][0])) for j in range(dim)]
            for j in range(dim):
                ant[j] = max(bounds[j][0], min(bounds[j][1], ant[j]))
            new_archive.append(ant)

        archive = new_archive
        archive_fitness = [f(sol) for sol in archive]

    for i in range(len(archive)):
        if archive_fitness[i] < best_val:
            best = copy.deepcopy(archive[i])
            best_val = archive_fitness[i]

    return best
