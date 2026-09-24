from spatial_reasoning.map_parser import GridMap, parse_grid_map
from spatial_reasoning.spatial_planner import AStarPlanner, Plan


LINEAR_GRID = """\
S.G
"""


BLOCKED_GRID = """\
S#G
"""


class TestAStarPlanner:
    def test_linear_path(self):
        grid = parse_grid_map(LINEAR_GRID)
        planner = AStarPlanner()
        plan = planner.plan_grid(grid)
        assert plan.success is True
        assert plan.path == [(0, 0), (1, 0), (2, 0)]
        assert plan.cost == 2.0

    def test_blocked_returns_failure(self):
        grid = parse_grid_map(BLOCKED_GRID)
        planner = AStarPlanner()
        plan = planner.plan_grid(grid)
        assert plan.success is False

    def test_no_start_or_goal(self):
        grid = GridMap(2, 2)
        planner = AStarPlanner()
        plan = planner.plan_grid(grid)
        assert plan.success is False

    def test_plan_graph(self):
        from spatial_reasoning.map_parser import parse_graph_map
        edges = [("s", "m", 1.0), ("m", "g", 1.0)]
        graph = parse_graph_map(edges, "s", "g")
        planner = AStarPlanner()
        plan = planner.plan_graph(graph, "s", "g")
        assert plan.success is True
        assert plan.path == ["s", "m", "g"]
        assert plan.cost == 2.0

    def test_plan_graph_disconnected(self):
        from spatial_reasoning.map_parser import parse_graph_map
        edges = [("s", "m", 1.0)]
        graph = parse_graph_map(edges, "s", "g")
        planner = AStarPlanner()
        plan = planner.plan_graph(graph, "s", "g")
        assert plan.success is False


class TestPlan:
    def test_repr(self):
        p = Plan(path=[(0, 0)], cost=0.0, success=True)
        assert p.success is True
