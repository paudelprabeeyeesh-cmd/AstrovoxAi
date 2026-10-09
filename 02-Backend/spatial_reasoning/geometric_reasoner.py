from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Point2D:
    x: float = 0.0
    y: float = 0.0


@dataclass
class Point3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Vector2D:
    x: float = 0.0
    y: float = 0.0

    def magnitude(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def normalize(self) -> "Vector2D":
        m = self.magnitude()
        if m < 1e-12:
            return Vector2D(0.0, 0.0)
        return Vector2D(self.x / m, self.y / m)

    def dot(self, other: "Vector2D") -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: "Vector2D") -> float:
        return self.x * other.y - self.y * other.x


@dataclass
class Vector3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def magnitude(self) -> float:
        return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5

    def normalize(self) -> "Vector3D":
        m = self.magnitude()
        if m < 1e-12:
            return Vector3D(0.0, 0.0, 0.0)
        return Vector3D(self.x / m, self.y / m, self.z / m)

    def dot(self, other: "Vector3D") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vector3D") -> "Vector3D":
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )


@dataclass
class BoundingBox2D:
    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 1.0
    max_y: float = 1.0

    def contains(self, point: Point2D) -> bool:
        return self.min_x <= point.x <= self.max_x and self.min_y <= point.y <= self.max_y


@dataclass
class BoundingBox3D:
    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = 0.0
    max_x: float = 1.0
    max_y: float = 1.0
    max_z: float = 1.0

    def contains(self, point: Point3D) -> bool:
        return (
            self.min_x <= point.x <= self.max_x
            and self.min_y <= point.y <= self.max_y
            and self.min_z <= point.z <= self.max_z
        )


def distance(a: Point2D, b: Point2D) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def distance_3d(a: Point3D, b: Point3D) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5


def angle_between(v1: Vector2D, v2: Vector2D) -> float:
    dot = v1.normalize().dot(v2.normalize())
    dot = max(-1.0, min(1.0, dot))
    return __import__("math").acos(dot)


def rotate_2d(point: Point2D, angle_rad: float, origin: Optional[Point2D] = None) -> Point2D:
    if origin is None:
        origin = Point2D(0.0, 0.0)
    dx = point.x - origin.x
    dy = point.y - origin.y
    cos_a = __import__("math").cos(angle_rad)
    sin_a = __import__("math").sin(angle_rad)
    return Point2D(
        origin.x + dx * cos_a - dy * sin_a,
        origin.y + dx * sin_a + dy * cos_a,
    )


def intersects_2d(a: Point2D, b: Point2D, c: Point2D, d: Point2D) -> bool:
    def ccw(p1: Point2D, p2: Point2D, p3: Point2D) -> bool:
        return (p3.y - p1.y) * (p2.x - p1.x) > (p2.y - p1.y) * (p3.x - p1.x)

    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)
