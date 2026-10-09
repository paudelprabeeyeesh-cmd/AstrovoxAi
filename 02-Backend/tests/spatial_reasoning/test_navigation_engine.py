import math

from spatial_reasoning.geometric_reasoner import Point2D
from spatial_reasoning.map_parser import GridMap, parse_grid_map
from spatial_reasoning.navigation_engine import NavigationEngine, NavigationResult, NavigationState


LINEAR_GRID = """\
S.G
"""


class TestNavigationState:
    def test_defaults(self):
        s = NavigationState()
        assert s.x == 0.0
        assert s.y == 0.0
        assert s.z == 0.0
        assert s.heading == 0.0

    def test_custom_values(self):
        s = NavigationState(x=1.0, y=2.0, z=3.0, heading=math.pi)
        assert s.x == 1.0
        assert s.y == 2.0
        assert s.z == 3.0
        assert abs(s.heading - math.pi) < 1e-9


class TestNavigationResult:
    def test_success_repr(self):
        r = NavigationResult(reached=True, path=[], message="complete")
        assert r.reached is True
        assert r.message == "complete"

    def test_failure_repr(self):
        r = NavigationResult(reached=False, path=[], message="blocked")
        assert r.reached is False
        assert r.message == "blocked"


class TestNavigationEngine:
    def test_follow_path(self):
        engine = NavigationEngine()
        result = engine.follow_path_2d([(0, 0), (1, 0), (2, 0)])
        assert result.reached is True
        assert len(result.path) == 3
        assert result.path[0].x == 0.0
        assert result.path[-1].x == 2.0

    def test_empty_path_returns_failure(self):
        engine = NavigationEngine()
        result = engine.follow_path_2d([])
        assert result.reached is False
        assert result.message == "empty path"

    def test_obstacle_block(self):
        engine = NavigationEngine()
        engine.register_obstacle(1.0, 0.0, radius=0.6)
        result = engine.follow_path_2d([(0, 0), (1, 0), (2, 0)])
        assert result.reached is False
        assert result.message == "blocked"

    def test_heading_set_correctly(self):
        engine = NavigationEngine()
        result = engine.follow_path_2d([(0, 0), (1, 0)])
        assert len(result.path) == 2
        assert abs(result.path[1].heading - 0.0) < 1e-9

    def test_multiple_obstacles_block(self):
        engine = NavigationEngine()
        engine.register_obstacle(0.5, 0.0, radius=1.0)
        engine.register_obstacle(3.0, 0.0, radius=1.0)
        result = engine.follow_path_2d([(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)])
        assert result.reached is False

    def test_no_obstacles_clear_path(self):
        engine = NavigationEngine()
        result = engine.follow_path_2d([(0, 0), (5, 5)])
        assert result.reached is True
        assert result.message == "complete"

    def test_speed_stored(self):
        engine = NavigationEngine(speed=2.5)
        assert engine.speed == 2.5

    def test_plan_and_follow_success(self):
        engine = NavigationEngine()
        grid = parse_grid_map(LINEAR_GRID)
        result = engine.plan_and_follow(grid)
        assert result.reached is True

    def test_plan_and_follow_blocked(self):
        engine = NavigationEngine()
        grid = GridMap(3, 1)
        grid.set_cell(0, 0, "start")
        grid.set_cell(2, 0, "goal")
        grid.set_cell(1, 0, "wall")
        result = engine.plan_and_follow(grid)
        assert result.reached is False


class TestRayCircleIntersect:
    def test_ray_hits_circle(self):
        from spatial_reasoning.navigation_engine import _ray_circle_intersect
        p1 = Point2D(0.0, 0.0)
        p2 = Point2D(2.0, 0.0)
        center = Point2D(1.0, 0.0)
        assert _ray_circle_intersect(p1, p2, center, 0.5)

    def test_ray_misses_circle(self):
        from spatial_reasoning.navigation_engine import _ray_circle_intersect
        p1 = Point2D(0.0, 0.0)
        p2 = Point2D(2.0, 0.0)
        center = Point2D(1.0, 5.0)
        assert not _ray_circle_intersect(p1, p2, center, 0.5)

    def test_zero_length_ray(self):
        from spatial_reasoning.navigation_engine import _ray_circle_intersect
        p1 = Point2D(0.0, 0.0)
        p2 = Point2D(0.0, 0.0)
        center = Point2D(1.0, 0.0)
        assert not _ray_circle_intersect(p1, p2, center, 0.5)
