import numpy as np


def nelder_ead(f, x0, alpha=1.0, gamma=2.0, rho=0.5, sigma=0.5, max_iter=1000, tol=1e-6):
    simplex = np.array([np.copy(xi) for xi in x0])
    simplex.shape[1]
    values = np.array([f(xi) for xi in simplex])
    for _ in range(max_iter):
        idx_sorted = np.argsort(values)
        best, worst = idx_sorted[0], idx_sorted[-1]
        second_worst = idx_sorted[-2]
        centroid = np.mean(simplex[idx_sorted[:-1]], axis=0)
        reflection = centroid + alpha * (centroid - simplex[worst])
        f_r = f(reflection)
        if f_r < values[best]:
            expansion = centroid + gamma * (reflection - centroid)
            f_e = f(expansion)
            if f_e < f_r:
                simplex[worst] = expansion
                values[worst] = f_e
            else:
                simplex[worst] = reflection
                values[worst] = f_r
        elif f_r < values[second_worst]:
            simplex[worst] = reflection
            values[worst] = f_r
        else:
            contraction = centroid + rho * (simplex[worst] - centroid)
            f_c = f(contraction)
            if f_c < values[worst]:
                simplex[worst] = contraction
                values[worst] = f_c
            else:
                for i in range(len(simplex)):
                    if i != best:
                        simplex[i] = simplex[best] + sigma * (simplex[i] - simplex[best])
                        values[i] = f(simplex[i])
        if abs(values[best] - values[worst]) < tol:
            break
    return simplex[best]


def pattern_search(f, x0, step_size=1.0, reduction=0.5, max_iter=100, tol=1e-6):
    x = np.copy(x0)
    step = step_size
    for _ in range(max_iter):
        improved = False
        for i in range(len(x)):
            for sign in [-1, 1]:
                x_new = np.copy(x)
                x_new[i] += sign * step
                if f(x_new) < f(x):
                    x = x_new
                    improved = True
                    break
        if not improved:
            step *= reduction
            if step < tol:
                break
    return x


def differential_evolution(f, bounds, pop_size=20, F=0.8, CR=0.9, max_iter=100):
    dim = len(bounds)
    pop = np.array([np.random.uniform(bnd[0], bnd[1], dim) for bnd in bounds for _ in range(pop_size // len(bounds))])
    if len(pop) < pop_size:
        extra = np.array([np.random.uniform(bnd[0], bnd[1], dim) for bnd in bounds for _ in range(pop_size - len(pop))])
        pop = np.vstack([pop, extra])
    fitness = np.array([f(ind) for ind in pop])
    for _ in range(max_iter):
        for i in range(pop_size):
            idxs = [j for j in range(pop_size) if j != i]
            a, b, c = np.random.choice(idxs, 3, replace=False)
            mutant = pop[a] + F * (pop[b] - pop[c])
            mutant = np.clip(mutant, [bnd[0] for bnd in bounds], [bnd[1] for bnd in bounds])
            cross = np.random.rand(dim) < CR
            if not np.any(cross):
                cross[np.random.randint(0, dim)] = True
            trial = np.where(cross, mutant, pop[i])
            f_trial = f(trial)
            if f_trial < fitness[i]:
                pop[i] = trial
                fitness[i] = f_trial
    best_idx = np.argmin(fitness)
    return pop[best_idx]
