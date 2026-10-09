import numpy as np


def dominates(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return bool(np.all(a <= b) and np.any(a < b))


def non_dominated_sort(pop, objs):
    n = len(pop)
    domination = [set() for _ in range(n)]
    dominated_by = [0] * n
    fronts = [[]]
    for i in range(n):
        for j in range(n):
            if i != j and dominates(objs[i], objs[j]):
                domination[i].add(j)
            elif i != j and dominates(objs[j], objs[i]):
                dominated_by[i] += 1
        if dominated_by[i] == 0:
            fronts[0].append(i)
    idx = 0
    while fronts[idx]:
        next_front = []
        for i in fronts[idx]:
            for j in domination[i]:
                dominated_by[j] -= 1
                if dominated_by[j] == 0:
                    next_front.append(j)
        idx += 1
        fronts.append(next_front)
    return fronts[:-1]


def crowding_distance(front, objs):
    n = len(front)
    if n == 0:
        return []
    distances = np.zeros(n)
    for m in range(objs.shape[1]):
        sorted_idx = np.argsort([objs[i][m] for i in front])
        distances[sorted_idx[0]] = float("inf")
        distances[sorted_idx[-1]] = float("inf")
        f_min = objs[front[sorted_idx[0]]][m]
        f_max = objs[front[sorted_idx[-1]]][m]
        if f_max == f_min:
            continue
        for k in range(1, n - 1):
            distances[sorted_idx[k]] += (
                objs[front[sorted_idx[k + 1]]][m]
                - objs[front[sorted_idx[k - 1]]][m]
            ) / (f_max - f_min)
    return distances


def pareto_front(pop, objs):
    fronts = non_dominated_sort(pop, objs)
    return fronts[0] if fronts else []
