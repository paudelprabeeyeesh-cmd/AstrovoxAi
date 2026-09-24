import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .geometric_reasoner import Point2D, Point3D, distance, distance_3d
from .map_parser import GridMap


@dataclass
class NavigationState:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    heading: float = 0.0


@dataclass
class NavigationResult:
    reached: bool
    path: List[NavigationState]
    message: str = ""


class NavigationEngine:
    def __init__(self, speed: float = 1.0):
        self.speed = speed
        self.obstacles: List[Tuple[Point2D, float]] = []

    def register_obstacle(self, x: float, y: float, radius: float = 0.5) -> None:
        self.obstacles.append((Point2D(x, y), radius))

    def follow_path_2d(self, path: List[Tuple[int, int]]) -> NavigationResult:
        if not path:
            return NavigationResult(reached=False, path=[], message="empty path")
        states: List[NavigationState] = []
        current = NavigationState(x=float(path[0][0]), y=float(path[0][1]))
        states.append(current)
        for target_x, target_y in path[1:]:
            target = Point2D(target_x, target_y)
            current_pos = Point2D(current.x, current.y)
            if self._is_blocked(current_pos, target):
                return NavigationResult(reached=False, path=states, message="blocked")
            current.x = float(target_x)
            current.y = float(target_y)
            current.heading = math.atan2(target_y - states[-1].y, target_x - states[-1].x)
            states.append(current)
        return NavigationResult(reached=True, path=states, message="complete")

    def plan_and_follow(self, grid: GridMap) -> NavigationResult:
        from .spatial_planner import AStarPlanner
        planner = AStarPlanner()
        plan = planner.plan_grid(grid)
        if not plan.success:
            return NavigationResult(reached=False, path=[], message="no path found")
        return self.follow_path_2d(plan.path)

    def _is_blocked(self, start: Point2D, end: Point2D) -> bool:
        for center, radius in self.obstacles:
            if _ray_circle_intersect(start, end, center, radius):
                return True
        return False


def _ray_circle_intersect(p1: Point2D, p2: Point2D, center: Point2D, radius: float) -> bool:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    fx = p1.x - center.x
    fy = p1.y - center.y
    a = dx * dx + dy * dy
    if a < 1e-12:
        return distance(p1, center) <= radius
    b = 2.0 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - radius * radius
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0.0:
        return False
    discriminant = discriminant ** 0.5
    t1 = (-b - discriminant) / (2.0 * a)
    t2 = (-b + discriminant) / (2.0 * a)
    return (0.0 <= t1 <= 1.0) or (0.0 <= t2 <= 1.0) or (t1 < 0.0 < t2)
