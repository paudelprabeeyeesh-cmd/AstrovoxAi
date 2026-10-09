from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class GridCell:
    x: int
    y: int
    kind: str = "empty"


class GridMap:
    def __init__(self, width: int = 0, height: int = 0, default: str = "empty"):
        self.width = width
        self.height = height
        self.grid: List[List[str]] = [[default for _ in range(width)] for _ in range(height)]
        self.start: Optional[Tuple[int, int]] = None
        self.goal: Optional[Tuple[int, int]] = None

    def set_cell(self, x: int, y: int, kind: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = kind
            if kind == "start":
                self.start = (x, y)
            elif kind == "goal":
                self.goal = (x, y)

    def is_walkable(self, x: int, y: int) -> bool:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return self.grid[y][x] != "wall"

    def neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        result = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                result.append((nx, ny))
        return result


class GraphMap:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, float]] = {}
        self.node_attrs: Dict[str, Dict[str, Any]] = {}
        self.start_node: Optional[str] = None
        self.goal_node: Optional[str] = None

    def add_node(self, node_id: str, **properties: Any) -> None:
        self.nodes.setdefault(node_id, {})
        if properties:
            self.node_attrs[node_id] = dict(properties)

    def add_edge(self, a: str, b: str, weight: float = 1.0) -> None:
        self.nodes.setdefault(a, {})[b] = weight
        self.nodes.setdefault(b, {})[a] = weight

    def neighbors(self, node_id: str) -> Dict[str, float]:
        return self.nodes.get(node_id, {})

    def get_properties(self, node_id: str) -> Dict[str, Any]:
        return dict(self.node_attrs.get(node_id, {}))


def parse_grid_map(raw: str) -> GridMap:
    lines = [line.rstrip("\n") for line in raw.splitlines() if line.strip() != ""]
    height = len(lines)
    width = max((len(line) for line in lines), default=0)
    grid = GridMap(width=width, height=height, default="empty")
    symbol_map = {"#": "wall", ".": "empty", "S": "start", "G": "goal"}
    for y, line in enumerate(lines):
        for x, ch in enumerate(line):
            kind = symbol_map.get(ch, "empty")
            grid.set_cell(x, y, kind)
    return grid


def parse_graph_map(edges: List[Tuple[str, str, float]], start: str, goal: str) -> GraphMap:
    graph = GraphMap()
    graph.start_node = start
    graph.goal_node = goal
    for a, b, w in edges:
        graph.add_edge(a, b, w)
    return graph
