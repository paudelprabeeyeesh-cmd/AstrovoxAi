import numpy as np


def nelder_ead(f, x0, alpha=1.0, gamma=2.0, rho=0.5, sigma=0.5, max_iter=1000, tol=1e-6):
    x = [np.copy(xi) for xi in x0]
    n = len(x0[0])
    values = [f(xi) for xi in x]
    for _ in range(max_iter):
        x_sorted = [xi for _, xi in sorted(zip(values, x))]
        values.sort()
        x_worst, x_best, x_second_best = x_sorted[-1], x_sorted[0], x_sorted[1]
        centroid = sum(x_sorted[:-1]) / (len(x_sorted) - 1)
        reflection = centroid + alpha * (centroid - x_worst)
        f_r = f(reflection)
        if f_r < values[0]:
            expansion = centroid + gamma * (reflection - centroid)
            f_e = f(expansion)
            if f_e < f_r:
                x[-1] = expansion
                values[-1] = f_e
            else:
                x[-1] = reflection
                values[-1] = f_r
        elif f_r < values[-2]:
            x[-1] = reflection
            values[-1] = f_r
        else:
            contraction = centroid + rho * (x_worst - centroid)
            f_c = f(contraction)
            if f_c < values[-1]:
                x[-1] = contraction
                values[-1] = f_c
            else:
                for i in range(1, len(x)):
                    x[i] = x_best + sigma * (x[i] - x_best)
                    values[i] = f(x[i])
        if abs(values[0] - values[-1]) < tol:
            break
    return x[0]


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
    pop = np.array([np.random.uniform(b[0], b[1], dim) for _ in range(pop_size)])
    fitness = np.array([f(ind) for ind in pop])
    for _ in range(max_iter):
        for i in range(pop_size):
            a, b, c = np.random.choice(pop_size, 3, replace=False)
            mutant = pop[a] + F * (pop[b] - pop[c])
            mutant = np.clip(mutant, [b[0] for b in bounds], [b[1] for b in bounds])
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
