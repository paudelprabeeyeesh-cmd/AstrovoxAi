import copy
import math
import random


def simulated_annealing(f, x0, bounds=None, T=1.0, alpha=0.99, max_iter=1000, tol=1e-6):
    x = copy.deepcopy(x0)
    n = len(x)
    best = copy.deepcopy(x)
    best_val = f(best)
    current_val = best_val

    for _ in range(max_iter):
        x_new = copy.deepcopy(x)
        idx = random.randint(0, n - 1)
        step = random.gauss(0, T)
        if bounds is not None:
            x_new[idx] = max(bounds[idx][0], min(bounds[idx][1], x_new[idx] + step))
        else:
            x_new[idx] = x_new[idx] + step

        new_val = f(x_new)
        if new_val < current_val or random.random() < math.exp((current_val - new_val) / T):
            x = x_new
            current_val = new_val
            if new_val < best_val:
                best = copy.deepcopy(x_new)
                best_val = new_val

        T *= alpha
        if T < tol:
            break

    return best
