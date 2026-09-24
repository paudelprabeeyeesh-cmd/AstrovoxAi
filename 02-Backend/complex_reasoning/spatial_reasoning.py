import numpy as np
from typing import List, Tuple, Optional


class SpatialRelation:
    def __init__(self, relation_type: str, object1: str, object2: str, vector: Optional[np.ndarray] = None):
        self.relation_type = relation_type
        self.object1 = object1
        self.object2 = object2
        self.vector = vector or np.zeros(3)

    def distance(self) -> float:
        return float(np.linalg.norm(self.vector))

    def direction(self) -> np.ndarray:
        norm = np.linalg.norm(self.vector)
        if norm == 0:
            return self.vector.copy()
        return self.vector / norm

    def __repr__(self):
        return f"{self.relation_type}({self.object1}, {self.object2})"


class SpatialObject:
    def __init__(self, name: str, position: Optional[np.ndarray] = None, dimensions: Optional[np.ndarray] = None):
        self.name = name
        self.position = position if position is not None else np.zeros(3)
        self.dimensions = dimensions if dimensions is not None else np.ones(3)
        self.orientation: float = 0.0

    def translate(self, vector: np.ndarray):
        self.position = self.position + vector

    def rotate(self, angle: float, axis: int = 2):
        c, s = np.cos(angle), np.sin(angle)
        if axis == 0:
            r = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        elif axis == 1:
            r = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        else:
            r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        self.position = r @ self.position
        self.orientation += angle

    def scale(self, factor: float):
        self.dimensions = self.dimensions * factor

    def distance_to(self, other: "SpatialObject") -> float:
        return float(np.linalg.norm(self.position - other.position))

    def contains(self, other: "SpatialObject") -> bool:
        half_dim = self.dimensions / 2
        pos = other.position
        return bool(np.all(np.abs(pos - self.position) <= half_dim))


class SpatialScene:
    def __init__(self):
        self.objects: Dict[str, SpatialObject] = {}
        self.relations: List[SpatialRelation] = []

    def add_object(self, obj: SpatialObject):
        self.objects[obj.name] = obj

    def rotate(self, angle: float, axis: int = 2):
        for obj in self.objects.values():
            obj.rotate(angle, axis)

    def translate(self, vector: np.ndarray):
        for obj in self.objects.values():
            obj.translate(vector)

    def distance(self, obj1: str, obj2: str) -> float:
        if obj1 not in self.objects or obj2 not in self.objects:
            return 0.0
        return self.objects[obj1].distance_to(self.objects[obj2])

    def mental_rotation(self, obj_name: str, angle: float, axis: int = 2) -> np.ndarray:
        if obj_name not in self.objects:
            return np.zeros(3)
        original = self.objects[obj_name].position.copy()
        self.objects[obj_name].rotate(angle, axis)
        return self.objects[obj_name].position - original

    def scene_distance(self) -> float:
        if len(self.objects) < 2:
            return 0.0
        positions = np.array([obj.position for obj in self.objects.values()])
        return float(np.var(np.linalg.norm(positions - positions.mean(axis=0), axis=1)))

    def topological_relation(self, obj1: str, obj2: str) -> str:
        if obj1 not in self.objects or obj2 not in self.objects:
            return "unknown"
        o1 = self.objects[obj1].position
        o2 = self.objects[obj2].position
        if np.allclose(o1, o2):
            return "equals"
        if np.linalg.norm(o1 - o2) < 0.1:
            return "touches"
        if np.linalg.norm(o1 - o2) < 1.0:
            return "near"
        return "far"
