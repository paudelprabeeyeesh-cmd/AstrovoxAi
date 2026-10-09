from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class Pose3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    def to_matrix(self) -> np.ndarray:
        cr = np.cos(self.roll)
        sr = np.sin(self.roll)
        cp = np.cos(self.pitch)
        sp = np.sin(self.pitch)
        cy = np.cos(self.yaw)
        sy = np.sin(self.yaw)
        return np.array([
            [cp * cy, cr * sp * cy - sr * sy, sr * sp * cy + cr * sy, self.x],
            [cp * sy, cr * sp * sy + sr * cy, sr * sp * sy - cr * cy, self.y],
            [-sp, cr * cp, sr * cp, self.z],
            [0.0, 0.0, 0.0, 1.0],
        ])

    def transform_point(self, point: np.ndarray) -> np.ndarray:
        m = self.to_matrix()
        return (m @ np.append(point, 1.0))[:3]


class SpatialGraph:
    def __init__(self):
        self.nodes: Dict[str, Pose3D] = {}
        self.edges: List[Tuple[str, str, float]] = []

    def add_node(self, node_id: str, pose: Pose3D) -> None:
        self.nodes[node_id] = pose

    def add_edge(self, a: str, b: str, distance: float) -> None:
        self.edges.append((a, b, distance))

    def shortest_path(self, start: str, end: str) -> Optional[List[str]]:
        if start not in self.nodes or end not in self.nodes:
            return None
        queue = [(start, [start])]
        visited = {start}
        adjacency: Dict[str, List[str]] = {n: [] for n in self.nodes}
        for a, b, _ in self.edges:
            adjacency[a].append(b)
            adjacency[b].append(a)
        while queue:
            current, path = queue.pop(0)
            if current == end:
                return path
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def distance(self, a: str, b: str) -> float:
        pa = self.nodes.get(a)
        pb = self.nodes.get(b)
        if pa is None or pb is None:
            return float("inf")
        return float(np.linalg.norm(np.array([pa.x - pb.x, pa.y - pb.y, pa.z - pb.z])))


class SpatialReasoner:
    def __init__(self):
        self.graph = SpatialGraph()
        self.obstacles: List[np.ndarray] = []

    def register_object(self, object_id: str, position: np.ndarray, orientation: Pose3D = None) -> None:
        pose = orientation if orientation is not None else Pose3D(x=position[0], y=position[1], z=position[2])
        self.graph.add_node(object_id, pose)

    def register_obstacle(self, position: np.ndarray, radius: float = 0.5) -> None:
        self.obstacles.append(np.array([*position, radius]))

    def navigate(self, start: str, goal: str) -> Optional[List[str]]:
        return self.graph.shortest_path(start, goal)

    def line_of_sight(self, a: str, b: str) -> bool:
        pa = self.graph.nodes.get(a)
        pb = self.graph.nodes.get(b)
        if pa is None or pb is None:
            return False
        start = np.array([pa.x, pa.y, pa.z])
        end = np.array([pb.x, pb.y, pb.z])
        direction = end - start
        distance = np.linalg.norm(direction)
        if distance < 1e-6:
            return True
        direction = direction / distance
        for obs in self.obstacles:
            obs_pos = obs[:3]
            obs_radius = obs[3]
            to_obs = obs_pos - start
            t = np.dot(to_obs, direction)
            if 0 <= t <= distance:
                closest = start + t * direction
                if np.linalg.norm(closest - obs_pos) < obs_radius:
                    return False
        return True
