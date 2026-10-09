import math
import random


def simulated_quantum_annealing(objective, x0, T_start=1.0, T_end=1e-4, steps=1000, tunneling_strength=0.5):
    x = list(x0)
    dim = len(x)
    current = objective(x)
    best_x = list(x)
    best_val = current
    for t in range(steps):
        T = T_start * (T_end / T_start) ** (t / steps)
        idx = random.randrange(dim)
        delta = random.gauss(0, math.sqrt(T)) + tunneling_strength * math.tanh(random.uniform(-1, 1) * T)
        x_new = list(x)
        x_new[idx] += delta
        new_val = objective(x_new)
        if new_val < current or random.random() < math.exp(-(new_val - current) / max(T, 1e-12)):
            x = x_new
            current = new_val
            if new_val < best_val:
                best_x = list(x_new)
                best_val = current
    return best_x
