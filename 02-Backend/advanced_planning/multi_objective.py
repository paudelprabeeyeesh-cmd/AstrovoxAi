
import numpy as np
from typing import Any, Dict, List, Optional, Tuple


class MultiObjectiveEvaluator:
    def __init__(self, num_objectives: int, objective_names: Optional[List[str]] = None):
        self.num_objectives = num_objectives
        self.objective_names = objective_names or [f"obj_{i}" for i in range(num_objectives)]

    def evaluate(self, solution: Dict[str, Any]) -> np.ndarray:
        return np.array(solution.get("objectives", [0.0] * self.num_objectives))

    def dominates(self, a: np.ndarray, b: np.ndarray) -> bool:
        better_or_equal = a <= b
        strictly_better = a < b
        return np.all(better_or_equal) and np.any(strictly_better)

    def non_dominated_sort(self, population: List[Dict[str, Any]]) -> List[List[int]]:
        fronts: List[List[int]] = []
        n = len(population)
        if n == 0:
            return fronts
        objectives = np.array([self.evaluate(ind) for ind in population])
        domination = np.zeros((n, n), dtype=bool)
        dominated_by = [[] for _ in range(n)]
        rank = np.full(n, -1)
        for i in range(n):
            for j in range(n):
                if i != j:
                    domination[i, j] = self.dominates(objectives[i], objectives[j])
                    if domination[i, j]:
                        dominated_by[j].append(i)
        current_front = [i for i in range(n) if not dominated_by[i]]
        rank[current_front] = 0
        fronts.append(current_front)
        front_idx = 0
        while True:
            next_front = []
            for i in fronts[front_idx]:
                for j in dominated_by[i]:
                    if rank[j] == front_idx + 1:
                        if j not in next_front:
                            next_front.append(j)
                    else:
                        rank[j] = front_idx + 1
                        if j not in next_front:
                            next_front.append(j)
            if not next_front:
                break
            fronts.append(next_front)
            front_idx += 1
        return fronts

    def crowding_distance(self, front_indices: List[int], objectives: np.ndarray) -> Dict[int, float]:
        n = len(front_indices)
        distances = {i: 0.0 for i in front_indices}
        if n <= 2:
            for i in front_indices:
                distances[i] = float("inf")
            return distances
        for m in range(self.num_objectives):
            sorted_idx = sorted(front_indices, key=lambda i: objectives[i, m])
            min_val = objectives[sorted_idx[0], m]
            max_val = objectives[sorted_idx[-1], m]
            distances[sorted_idx[0]] = float("inf")
            distances[sorted_idx[-1]] = float("inf")
            for k in range(1, n - 1):
                idx = sorted_idx[k]
                prev_val = objectives[sorted_idx[k - 1], m]
                next_val = objectives[sorted_idx[k + 1], m]
                if max_val > min_val:
                    distances[idx] += (next_val - prev_val) / (max_val - min_val)
        return distances


class NSGAII:
    def __init__(self, evaluator: MultiObjectiveEvaluator, population_size: int = 50,
                 mutation_rate: float = 0.1, crossover_rate: float = 0.7):
        self.evaluator = evaluator
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.history: List[List[Dict[str, Any]]] = []

    def initialize_population(self, bounds: List[Tuple[float, float]], size: int) -> List[Dict[str, Any]]:
        population = []
        for _ in range(size):
            solution = {"genes": np.array([np.random.uniform(lo, hi) for lo, hi in bounds])}
            solution["objectives"] = self._compute_objectives(solution["genes"], bounds)
            population.append(solution)
        return population

    def _compute_objectives(self, genes: np.ndarray, bounds: List[Tuple[float, float]]) -> List[float]:
        normalized = (genes - np.array([lo for lo, _ in bounds])) / (np.array([hi - lo for lo, hi in bounds]) + 1e-9)
        objs = []
        objs.append(float(np.sum(normalized ** 2)))
        objs.append(float(np.sum((1 - normalized) ** 2)))
        return objs

    def tournament_select(self, population: List[Dict[str, Any]], ranks: np.ndarray, distances: Dict[int, float],
                         k: int = 2) -> int:
        indices = np.random.choice(len(population), k, replace=False)
        best = indices[0]
        for idx in indices[1:]:
            if ranks[idx] < ranks[best] or (ranks[idx] == ranks[best] and distances[idx] > distances[best]):
                best = idx
        return best

    def crossover(self, parent1: Dict, parent2: Dict) -> Tuple[Dict, Dict]:
        if np.random.random() > self.crossover_rate:
            return parent1, parent2
        genes1, genes2 = parent1["genes"], parent2["genes"]
        alpha = np.random.random()
        child1_genes = alpha * genes1 + (1 - alpha) * genes2
        child2_genes = alpha * genes2 + (1 - alpha) * genes1
        child1 = {"genes": child1_genes}
        child2 = {"genes": child2_genes}
        return child1, child2

    def mutate(self, individual: Dict, bounds: List[Tuple[float, float]]) -> Dict:
        genes = individual["genes"]
        mask = np.random.random(len(genes)) < self.mutation_rate
        noise = np.random.randn(len(genes)) * 0.1
        genes = np.where(mask, genes + noise, genes)
        for i, (lo, hi) in enumerate(bounds):
            genes[i] = np.clip(genes[i], lo, hi)
        individual["genes"] = genes
        individual["objectives"] = self._compute_objectives(genes, bounds)
        return individual

    def run(self, bounds: List[Tuple[float, float]], generations: int = 100) -> List[Dict[str, Any]]:
        population = self.initialize_population(bounds, self.population_size)
        for gen in range(generations):
            all_solutions = list(population)
            fronts = self.evaluator.non_dominated_sort(all_solutions)
            new_population: List[Dict] = []
            for front in fronts:
                if len(new_population) + len(front) <= self.population_size:
                    for idx in front:
                        new_population.append(dict(all_solutions[idx]))
                else:
                    remaining = self.population_size - len(new_population)
                    if remaining > 0 and front:
                        objs = np.array([self.evaluator.evaluate(all_solutions[i]) for i in front])
                        distances = self.evaluator.crowding_distance(front, objs)
                        sorted_front = sorted(front, key=lambda i: distances[i], reverse=True)
                        for idx in sorted_front[:remaining]:
                            new_population.append(dict(all_solutions[idx]))
                    break
            while len(new_population) < self.population_size:
                p1_idx = self.tournament_select(population,
                                                np.array([len(new_population)] * len(population)),
                                                {i: 0.0 for i in range(len(population))})
                p2_idx = self.tournament_select(population,
                                                np.array([len(new_population)] * len(population)),
                                                {i: 0.0 for i in range(len(population))})
                child1, child2 = self.crossover(population[p1_idx], population[p2_idx])
                child1 = self.mutate(child1, bounds)
                child2 = self.mutate(child2, bounds)
                new_population.append(child1)
                if len(new_population) < self.population_size:
                    new_population.append(child2)
            population = new_population[:self.population_size]
            self.history.append(list(population))
        pareto = self._get_pareto_front(population)
        return pareto

    def _get_pareto_front(self, population: List[Dict]) -> List[Dict]:
        fronts = self.evaluator.non_dominated_sort(population)
        return [population[i] for i in fronts[0]] if fronts else []
