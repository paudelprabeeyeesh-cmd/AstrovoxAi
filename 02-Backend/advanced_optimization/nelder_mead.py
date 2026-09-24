import numpy as np


def nelder_mead(f, x0, alpha=1.0, gamma=2.0, rho=0.5, sigma=0.5, max_iter=1000, tol=1e-6):
    simplex = np.array([np.copy(xi) for xi in x0])
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
