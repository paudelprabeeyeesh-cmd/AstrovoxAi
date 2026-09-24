import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .geometric_reasoner import Point2D, distance
from .map_parser import GridMap, GraphMap


@dataclass
class Plan:
    path: List[Tuple[int, int]]
    cost: float
    success: bool


class AStarPlanner:
    def __init__(self, allow_diagonal: bool = False):
        self.allow_diagonal = allow_diagonal

    def plan_grid(self, grid: GridMap) -> Plan:
        if grid.start is None or grid.goal is None:
            return Plan(path=[], cost=float("inf"), success=False)
        sx, sy = grid.start
        gx, gy = grid.goal
        start = (sx, sy)
        goal = (gx, gy)
        if start == goal:
            return Plan(path=[start], cost=0.0, success=True)
        open_set: List[Tuple[float, int, Tuple[int, int]]] = []
        import heapq
        heapq.heappush(open_set, (0.0, 0, start))
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {start: 0.0}
        counter = 0
        while open_set:
            _, _, current = heapq.heappop(open_set)
            if current == goal:
                path = _reconstruct(came_from, current)
                return Plan(path=path, cost=g_score[goal], success=True)
            for nx, ny in grid.neighbors(*current):
                neighbor = (nx, ny)
                step_cost = distance(Point2D(*current), Point2D(*neighbor))
                tentative_g = g_score[current] + step_cost
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + _heuristic(neighbor, goal)
                    counter += 1
                    heapq.heappush(open_set, (f, counter, neighbor))
        return Plan(path=[], cost=float("inf"), success=False)

    def plan_graph(self, graph: GraphMap, start: str, goal: str) -> Plan:
        if start not in graph.nodes or goal not in graph.nodes:
            return Plan(path=[], cost=float("inf"), success=False)
        if start == goal:
            return Plan(path=[start], cost=0.0, success=True)
        import heapq
        open_set: List[Tuple[float, int, str]] = []
        heapq.heappush(open_set, (0.0, 0, start))
        came_from: Dict[str, str] = {}
        g_score: Dict[str, float] = {start: 0.0}
        counter = 0
        while open_set:
            _, _, current = heapq.heappop(open_set)
            if current == goal:
                path = _reconstruct_str(came_from, current)
                return Plan(path=path, cost=g_score[goal], success=True)
            for neighbor, weight in graph.neighbors(current).items():
                tentative_g = g_score[current] + weight
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h = 0.0
                    counter += 1
                    heapq.heappush(open_set, (tentative_g + h, counter, neighbor))
        return Plan(path=[], cost=float("inf"), success=False)


def _heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _reconstruct(came_from: Dict[Tuple[int, int], Tuple[int, int]], current: Tuple[int, int]) -> List[Tuple[int, int]]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def _reconstruct_str(came_from: Dict[str, str], current: str) -> List[str]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
