from spatial_reasoning.map_parser import GridMap, GraphMap, parse_grid_map, parse_graph_map


SIMPLE_GRID = """\
S..
.#.
..G
"""


class TestGridMap:
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
