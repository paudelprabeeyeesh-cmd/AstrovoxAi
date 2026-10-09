import numpy as np
from .pareto_front import non_dominated_sort, crowding_distance


class NSGA2:
    def __init__(self, pop_size=50, max_iter=100):
        self.pop_size = pop_size
        self.max_iter = max_iter

    def optimize(self, obj_funcs, bounds):
        dim = len(bounds)
        pop = np.array(
            [
                [np.random.uniform(b[0], b[1]) for b in bounds]
                for _ in range(self.pop_size)
            ]
        )
        for _ in range(self.max_iter):
            _ = np.array([obj_funcs(ind) for ind in pop])
            offspring = np.array(
                [
                    [np.random.uniform(b[0], b[1]) for b in bounds]
                    for _ in range(self.pop_size)
                ]
            )
            combined = np.vstack([pop, offspring])
            combined_objs = np.array([obj_funcs(ind) for ind in combined])
            fronts = non_dominated_sort(range(len(combined)), combined_objs)
            new_pop = []
            for front in fronts:
                if len(new_pop) + len(front) <= self.pop_size:
                    new_pop.extend(front)
                else:
                    distances = crowding_distance(front, combined_objs)
                    sorted_front = [
                        f for _, f in sorted(zip(distances, front), reverse=True)
                    ]
                    new_pop.extend(sorted_front[: self.pop_size - len(new_pop)])
                    break
            pop = combined[new_pop]
        return pop
