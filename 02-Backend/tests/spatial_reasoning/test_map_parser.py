from spatial_reasoning.map_parser import GridMap, GridCell, GraphMap, parse_grid_map, parse_graph_map


SIMPLE_GRID = """\
S..
.#.
..G
"""

EMPTY_GRID = ""


class TestGridCell:
    def test_default_kind(self):
        cell = GridCell(x=0, y=0)
        assert cell.kind == "empty"

    def test_custom_kind(self):
        cell = GridCell(x=1, y=2, kind="wall")
        assert cell.kind == "wall"
    def test_parse(self):
        grid = parse_grid_map(SIMPLE_GRID)
        assert grid.width == 3
        assert grid.height == 3
        assert grid.start == (0, 0)
        assert grid.goal == (2, 2)

    def test_walkable(self):
        grid = parse_grid_map(SIMPLE_GRID)
        assert grid.is_walkable(0, 0)
        assert not grid.is_walkable(1, 1)
        assert grid.is_walkable(2, 2)

    def test_neighbors(self):
        grid = parse_grid_map(SIMPLE_GRID)
        n = grid.neighbors(0, 0)
        assert (1, 0) in n
        assert (0, 1) in n
        assert (-1, 0) not in n

    def test_set_cell(self):
        grid = GridMap(2, 2)
        grid.set_cell(0, 0, "start")
        grid.set_cell(1, 1, "goal")
        assert grid.start == (0, 0)
        assert grid.goal == (1, 1)

    def test_out_of_bounds_not_walkable(self):
        grid = GridMap(2, 2)
        assert not grid.is_walkable(-1, 0)
        assert not grid.is_walkable(0, -1)
        assert not grid.is_walkable(2, 0)
        assert not grid.is_walkable(0, 2)

    def test_out_of_bounds_neighbors_empty(self):
        grid = GridMap(2, 2)
        assert grid.neighbors(0, 0) == [(1, 0), (0, 1)]

    def test_custom_default(self):
        grid = GridMap(2, 2, default="wall")
        assert not grid.is_walkable(0, 0)

    def test_parse_empty_returns_zero_size(self):
        grid = parse_grid_map(EMPTY_GRID)
        assert grid.width == 0
        assert grid.height == 0


class TestGraphMap:
    def test_parse_graph(self):
        edges = [("a", "b", 1.0), ("b", "c", 2.0)]
        graph = parse_graph_map(edges, "a", "c")
        assert graph.start_node == "a"
        assert graph.goal_node == "c"
        assert graph.neighbors("b") == {"a": 1.0, "c": 2.0}

    def test_add_node_and_edge(self):
        graph = GraphMap()
        graph.add_node("x", label="start")
        graph.add_edge("x", "y", 5.0)
        assert graph.neighbors("x") == {"y": 5.0}

    def test_get_properties(self):
        graph = GraphMap()
        graph.add_node("x", label="start", weight=10)
        props = graph.get_properties("x")
        assert props["label"] == "start"
        assert props["weight"] == 10

    def test_get_properties_unknown_returns_empty(self):
        graph = GraphMap()
        assert graph.get_properties("unknown") == {}

    def test_neighbors_unknown_returns_empty(self):
        graph = GraphMap()
        assert graph.neighbors("unknown") == {}

    def test_start_goal_set_by_parse(self):
        edges = [("a", "b", 1.0)]
        graph = parse_graph_map(edges, "a", "b")
        assert graph.start_node == "a"
        assert graph.goal_node == "b"
