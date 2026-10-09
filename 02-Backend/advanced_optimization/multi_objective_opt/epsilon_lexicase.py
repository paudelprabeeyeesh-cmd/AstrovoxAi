import numpy as np


class EpsilonLexicase:
    def __init__(self, epsilon=0.0):
        self.epsilon = epsilon

    def select(self, pop, objs):
        pop = np.asarray(pop)
        objs = np.asarray(objs, dtype=float)
        candidates = list(range(len(pop)))
        objectives = list(range(objs.shape[1]))
        np.random.shuffle(objectives)
        for obj_idx in objectives:
            if len(candidates) <= 1:
                break
            best_val = np.min(objs[candidates, obj_idx])
            threshold = best_val + self.epsilon
            candidates = [i for i in candidates if objs[i, obj_idx] <= threshold]
        return pop[np.random.choice(candidates)]
