from spatial_reasoning.map_parser import GridMap, parse_grid_map
from spatial_reasoning.navigation_engine import NavigationEngine, NavigationResult


LINEAR_GRID = """\
S.G
"""


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
