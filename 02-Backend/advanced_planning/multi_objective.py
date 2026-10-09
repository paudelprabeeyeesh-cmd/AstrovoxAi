import math
import random
from typing import Any, Dict, List, Optional, Tuple


def _vec_len(v):
    return math.sqrt(sum(x * x for x in v))


def _vec_sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _vec_sum(v):
    return sum(v)


def _row_norm(v):
    s = math.sqrt(sum(x * x for x in v))
    return [x / max(s, 1e-10) for x in v]


class MultiObjectiveEvaluator:
    def __init__(self, num_objectives: int, objective_names: Optional[List[str]] = None):
        self.num_objectives = num_objectives
        self.objective_names = objective_names or [f"obj_{i}" for i in range(num_objectives)]

    def evaluate(self, solution: Dict[str, Any]) -> List[float]:
        return list(solution.get("objectives", [0.0] * self.num_objectives))

    def dominates(self, a: List[float], b: List[float]) -> bool:
        better_or_equal = [x <= y for x, y in zip(a, b)]
        strictly_better = [x < y for x, y in zip(a, b)]
        return all(better_or_equal) and any(strictly_better)

    def non_dominated_sort(self, population: List[Dict[str, Any]]) -> List[List[int]]:
        fronts: List[List[int]] = []
        n = len(population)
        if n == 0:
            return fronts
        objectives = [self.evaluate(ind) for ind in population]
        dominated_by: List[List[int]] = [[] for _ in range(n)]
        rank = [-1] * n
        for i in range(n):
            for j in range(n):
                if i != j and self.dominates(objectives[i], objectives[j]):
                    dominated_by[j].append(i)
        current_front = [i for i in range(n) if not dominated_by[i]]
        for i in current_front:
            rank[i] = 0
        fronts.append(current_front)
        front_idx = 0
        while front_idx < len(fronts):
            next_front = []
            for i in fronts[front_idx]:
                for j in dominated_by[i]:
                    if rank[j] == -1:
                        rank[j] = front_idx + 1
                        if j not in next_front:
                            next_front.append(j)
            if not next_front:
                break
            fronts.append(next_front)
            front_idx += 1
        return fronts

    def crowding_distance(self, front_indices: List[int], objectives: List[List[float]]) -> Dict[int, float]:
        n = len(front_indices)
        distances: Dict[int, float] = {i: 0.0 for i in front_indices}
        if n <= 2:
            for i in front_indices:
                distances[i] = float("inf")
            return distances
        for m in range(self.num_objectives):
            sorted_idx = sorted(front_indices, key=lambda i: objectives[i][m])
            min_val = objectives[sorted_idx[0]][m]
            max_val = objectives[sorted_idx[-1]][m]
            distances[sorted_idx[0]] = float("inf")
            distances[sorted_idx[-1]] = float("inf")
            for k in range(1, n - 1):
                idx = sorted_idx[k]
                prev_val = objectives[sorted_idx[k - 1]][m]
                next_val = objectives[sorted_idx[k + 1]][m]
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
            genes = [random.uniform(lo, hi) for lo, hi in bounds]
            solution = {"genes": genes, "objectives": self._compute_objectives(genes, bounds)}
            population.append(solution)
        return population

    def _compute_objectives(self, genes: List[float], bounds: List[Tuple[float, float]]) -> List[float]:
        los = [lo for lo, _ in bounds]
        his = [hi - lo for lo, hi in bounds]
        normalized = [(g - lo) / (hi + 1e-9) for g, lo, hi in zip(genes, los, his)]
        objs = []
        objs.append(sum(n ** 2 for n in normalized))
        objs.append(sum((1 - n) ** 2 for n in normalized))
        return objs

    def tournament_select(self, population: List[Dict[str, Any]], ranks: List[int],
                         distances: Dict[int, float], k: int = 2) -> int:
        indices = random.sample(range(len(population)), min(k, len(population)))
        best = indices[0]
        for idx in indices[1:]:
            if ranks[idx] < ranks[best] or (ranks[idx] == ranks[best] and distances.get(idx, 0.0) > distances.get(best, 0.0)):
                best = idx
        return best

    def crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if random.random() > self.crossover_rate:
            return parent1, parent2
        genes1, genes2 = parent1["genes"], parent2["genes"]
        alpha = random.random()
        child1_genes = [alpha * g1 + (1 - alpha) * g2 for g1, g2 in zip(genes1, genes2)]
        child2_genes = [alpha * g2 + (1 - alpha) * g1 for g1, g2 in zip(genes1, genes2)]
        return {"genes": child1_genes}, {"genes": child2_genes}

    def mutate(self, individual: Dict[str, Any], bounds: List[Tuple[float, float]]) -> Dict[str, Any]:
        genes = list(individual["genes"])
        mask = [random.random() < self.mutation_rate for _ in genes]
        noise = [random.gauss(0, 0.1) for _ in genes]
        genes = [g + n if m else g for g, n, m in zip(genes, noise, mask)]
        genes = [max(lo, min(hi, g)) for g, (lo, hi) in zip(genes, bounds)]
        individual["genes"] = genes
        individual["objectives"] = self._compute_objectives(genes, bounds)
        return individual

    def run(self, bounds: List[Tuple[float, float]], generations: int = 100) -> List[Dict[str, Any]]:
        population = self.initialize_population(bounds, self.population_size)
        for gen in range(generations):
            all_solutions = list(population)
            fronts = self.evaluator.non_dominated_sort(all_solutions)
            objs = [self.evaluator.evaluate(all_solutions[i]) for i in range(len(all_solutions))]
            new_population: List[Dict[str, Any]] = []
            for front in fronts:
                if len(new_population) + len(front) <= self.population_size:
                    for idx in front:
                        new_population.append(dict(all_solutions[idx]))
                else:
                    remaining = self.population_size - len(new_population)
                    if remaining > 0 and front:
                        distances = self.evaluator.crowding_distance(front, objs)
                        sorted_front = sorted(front, key=lambda i: distances.get(i, 0.0), reverse=True)
                        for idx in sorted_front[:remaining]:
                            new_population.append(dict(all_solutions[idx]))
                    break
            while len(new_population) < self.population_size:
                ranks = [0] * len(all_solutions)
                for fi, front in enumerate(fronts):
                    for idx in front:
                        ranks[idx] = fi
                pop_objs = [self.evaluator.evaluate(p) for p in all_solutions]
                current_fronts = self.evaluator.non_dominated_sort(all_solutions)
                distances = self.evaluator.crowding_distance([i for f in current_fronts for i in f], pop_objs) if current_fronts else {}
                p1_idx = self.tournament_select(all_solutions, ranks, distances)
                p2_idx = self.tournament_select(all_solutions, ranks, distances)
                c1, c2 = self.crossover(all_solutions[p1_idx], all_solutions[p2_idx])
                c1 = self.mutate(c1, bounds)
                c2 = self.mutate(c2, bounds)
                new_population.append(c1)
                if len(new_population) < self.population_size:
                    new_population.append(c2)
            population = new_population[:self.population_size]
            self.history.append(list(population))
        pareto = self._get_pareto_front(population)
        return pareto

    def _get_pareto_front(self, population: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        fronts = self.evaluator.non_dominated_sort(population)
        return [population[i] for i in fronts[0]] if fronts else []
