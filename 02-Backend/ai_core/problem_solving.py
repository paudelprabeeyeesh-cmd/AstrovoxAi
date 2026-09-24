import numpy as np
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import heapq


@dataclass
class SearchNode:
    state: Any
    parent: Optional["SearchNode"]
    action: Optional[Any]
    path_cost: float = 0.0
    depth: int = 0


class HeuristicSearch:
    def __init__(self, heuristic: Optional[Callable[[Any], float]] = None):
        self.heuristic = heuristic or (lambda s: 0.0)

    def astar(self, start: Any, goal_test: Callable[[Any], bool],
              expand: Callable[[Any], List[Tuple[Any, Any, float]]]) -> Optional[List[Any]]:
        frontier = [(self.heuristic(start), 0, SearchNode(state=start, parent=None, action=None))]
        explored = set()
        counter = 0
        while frontier:
            _, _, current = heapq.heappop(frontier)
            if goal_test(current.state):
                return self._path(current)
            if current.state in explored:
                continue
            explored.add(current.state)
            for neighbor_state, action, cost in expand(current.state):
                child = SearchNode(
                    state=neighbor_state,
                    parent=current,
                    action=action,
                    path_cost=current.path_cost + cost,
                    depth=current.depth + 1,
                )
                counter += 1
                h = self.heuristic(neighbor_state)
                heapq.heappush(frontier, (child.path_cost + h, counter, child))
        return None

    def greedy(self, start: Any, goal_test: Callable[[Any], bool],
               expand: Callable[[Any], List[Tuple[Any, Any, float]]]) -> Optional[List[Any]]:
        frontier = [(self.heuristic(start), 0, SearchNode(state=start, parent=None, action=None))]
        explored = set()
        counter = 0
        while frontier:
            _, _, current = heapq.heappop(frontier)
            if goal_test(current.state):
                return self._path(current)
            if current.state in explored:
                continue
            explored.add(current.state)
            for neighbor_state, action, _ in expand(current.state):
                child = SearchNode(state=neighbor_state, parent=current, action=action)
                counter += 1
                heapq.heappush(frontier, (self.heuristic(neighbor_state), counter, child))
        return None

    def _path(self, node: SearchNode) -> List[Any]:
        actions = []
        current = node
        while current.parent is not None:
            if current.action is not None:
                actions.append(current.action)
            current = current.parent
        return list(reversed(actions))


class ConstraintSatisfactionProblem:
    def __init__(self, variables: List[str], domains: Dict[str, List[Any]], constraints: List[Callable]):
        self.variables = variables
        self.domains = domains
        self.constraints = constraints

    def solve(self, assignment: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if assignment is None:
            assignment = {}
        if len(assignment) == len(self.variables):
            return assignment
        unassigned = [v for v in self.variables if v not in assignment]
        var = unassigned[0]
        for value in self._order_values(var, assignment):
            if self._consistent(var, value, assignment):
                new_assignment = {**assignment, var: value}
                result = self.solve(new_assignment)
                if result is not None:
                    return result
        return None

    def _order_values(self, var: str, assignment: Dict[str, Any]) -> List[Any]:
        return self.domains.get(var, [])

    def _consistent(self, var: str, value: Any, assignment: Dict[str, Any]) -> bool:
        test_assignment = {**assignment, var: value}
        for constraint in self.constraints:
            if not constraint(test_assignment):
                return False
        return True


class AnalogyEngine:
    def __init__(self):
        self.source_domain: Dict[str, Any] = {}
        self.target_domain: Dict[str, Any] = {}
        self.mapping: Dict[str, str] = {}

    def set_source(self, domain: Dict[str, Any]) -> None:
        self.source_domain = domain

    def set_target(self, domain: Dict[str, Any]) -> None:
        self.target_domain = domain

    def map_elements(self, pairs: List[Tuple[str, str]]) -> None:
        self.mapping = {a: b for a, b in pairs}

    def transfer(self, source_relation: str) -> Optional[Tuple[str, Any]]:
        target_concept = self.mapping.get(source_relation)
        if target_concept and target_concept in self.target_domain:
            return target_concept, self.target_domain[target_concept]
        return None

    def structural_alignment_score(self) -> float:
        if not self.mapping:
            return 0.0
        mapped_source_keys = set(self.mapping.keys())
        mapped_target_keys = set(self.mapping.values())
        return len(mapped_source_keys) / max(len(self.source_domain), 1)


class ProblemSolver:
    def __init__(self):
        self.search = HeuristicSearch()
        self.analogy = AnalogyEngine()
        self._solution_log: List[Dict[str, Any]] = []

    def search_solution(self, start: Any, goal_test: Callable[[Any], bool],
                        expand: Callable[[Any], List[Tuple[Any, Any, float]]],
                        method: str = "astar", heuristic: Optional[Callable[[Any], float]] = None) -> Optional[List[Any]]:
        searcher = HeuristicSearch(heuristic=heuristic)
        if method == "astar":
            solution = searcher.astar(start, goal_test, expand)
        elif method == "greedy":
            solution = searcher.greedy(start, goal_test, expand)
        else:
            raise ValueError(f"Unknown search method: {method}")
        self._solution_log.append({"method": method, "found": solution is not None, "length": len(solution) if solution else 0})
        return solution

    def solve_csp(self, variables: List[str], domains: Dict[str, List[Any]],
                  constraints: List[Callable]) -> Optional[Dict[str, Any]]:
        csp = ConstraintSatisfactionProblem(variables, domains, constraints)
        return csp.solve()

    def solve_by_analogy(self, source_domain: Dict[str, Any], target_domain: Dict[str, Any],
                         pairs: List[Tuple[str, str]]) -> Optional[Tuple[str, Any]]:
        self.analogy.set_source(source_domain)
        self.analogy.set_target(target_domain)
        self.analogy.map_elements(pairs)
        return self.analogy.transfer(next(iter(source_domain.keys())) if source_domain else None)

    def get_solution_log(self) -> List[Dict[str, Any]]:
        return list(self._solution_log)
