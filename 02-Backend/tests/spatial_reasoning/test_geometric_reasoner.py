import math

from spatial_reasoning.geometric_reasoner import (
    Point2D,
    Point3D,
    Vector2D,
    Vector3D,
    BoundingBox2D,
    BoundingBox3D,
    distance,
    distance_3d,
    angle_between,
    rotate_2d,
    intersects_2d,
)


class TestPoint2D:
    def test_defaults(self):
        p = Point2D()
        assert p.x == 0.0
        assert p.y == 0.0

    def test_distance(self):
        a = Point2D(0.0, 0.0)
        b = Point2D(3.0, 4.0)
        assert distance(a, b) == 5.0


class TestPoint3D:
    def test_distance_3d(self):
        a = Point3D(0.0, 0.0, 0.0)
        b = Point3D(1.0, 2.0, 2.0)
        assert distance_3d(a, b) == 3.0


class TestVector2D:
    def test_magnitude(self):
        v = Vector2D(3.0, 4.0)
        assert v.magnitude() == 5.0

    def test_normalize(self):
        v = Vector2D(3.0, 4.0)
        n = v.normalize()
        assert abs(n.magnitude() - 1.0) < 1e-9

    def test_normalize_zero_vector(self):
        v = Vector2D(0.0, 0.0)
        n = v.normalize()
        assert n.x == 0.0
        assert n.y == 0.0

    def test_dot(self):
        v1 = Vector2D(1.0, 0.0)
        v2 = Vector2D(0.0, 1.0)
        assert v1.dot(v2) == 0.0

    def test_cross(self):
        v1 = Vector2D(1.0, 0.0)
        v2 = Vector2D(0.0, 1.0)
        assert v1.cross(v2) == 1.0


class TestVector3D:
    def test_magnitude(self):
        v = Vector3D(1.0, 2.0, 2.0)
        assert v.magnitude() == 3.0

    def test_normalize(self):
        v = Vector3D(1.0, 2.0, 2.0)
        n = v.normalize()
        assert abs(n.magnitude() - 1.0) < 1e-9

    def test_normalize_zero_vector(self):
        v = Vector3D(0.0, 0.0, 0.0)
        n = v.normalize()
        assert n.x == 0.0
        assert n.y == 0.0
        assert n.z == 0.0

    def test_dot(self):
        v1 = Vector3D(1.0, 0.0, 0.0)
        v2 = Vector3D(0.0, 1.0, 0.0)
        assert v1.dot(v2) == 0.0

    def test_cross(self):
        v1 = Vector3D(1.0, 0.0, 0.0)
        v2 = Vector3D(0.0, 1.0, 0.0)
        c = v1.cross(v2)
        assert abs(c.x - 0.0) < 1e-9
        assert abs(c.y - 0.0) < 1e-9
        assert abs(c.z - 1.0) < 1e-9


class TestBoundingBox2D:
    def test_contains(self):
        box = BoundingBox2D(0.0, 0.0, 10.0, 10.0)
        assert box.contains(Point2D(5.0, 5.0))
        assert not box.contains(Point2D(11.0, 5.0))

    def test_edge_on_boundary(self):
        box = BoundingBox2D(0.0, 0.0, 10.0, 10.0)
        assert box.contains(Point2D(0.0, 5.0))
        assert box.contains(Point2D(10.0, 5.0))


class TestBoundingBox3D:
    def test_contains(self):
        box = BoundingBox3D(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
        assert box.contains(Point3D(5.0, 5.0, 5.0))
        assert not box.contains(Point3D(5.0, 5.0, 11.0))

    def test_edge_on_boundary(self):
        box = BoundingBox3D(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
        assert box.contains(Point3D(0.0, 0.0, 0.0))
        assert box.contains(Point3D(10.0, 10.0, 10.0))


class TestRotate2D:
    def test_rotate_90_degrees(self):
        p = Point2D(1.0, 0.0)
        r = rotate_2d(p, math.pi / 2)
        assert abs(r.x - 0.0) < 1e-9
        assert abs(r.y - 1.0) < 1e-9

    def test_rotate_about_custom_origin(self):
        p = Point2D(1.0, 1.0)
        r = rotate_2d(p, math.pi / 2, origin=Point2D(1.0, 0.0))
        assert abs(r.x - 0.0) < 1e-9
        assert abs(r.y - 0.0) < 1e-9


class TestIntersects2D:
    def test_intersecting_segments(self):
        a = Point2D(0.0, 0.0)
        b = Point2D(2.0, 2.0)
        c = Point2D(0.0, 2.0)
        d = Point2D(2.0, 0.0)
        assert intersects_2d(a, b, c, d)

    def test_non_intersecting_segments(self):
        a = Point2D(0.0, 0.0)
        b = Point2D(1.0, 1.0)
        c = Point2D(2.0, 0.0)
        d = Point2D(3.0, 1.0)
        assert not intersects_2d(a, b, c, d)

    def test_shared_endpoint(self):
        a = Point2D(0.0, 0.0)
        b = Point2D(1.0, 0.0)
        c = Point2D(1.0, 0.0)
        d = Point2D(2.0, 0.0)
        assert not intersects_2d(a, b, c, d)


class TestAngleBetween:
    def test_orthogonal(self):
        v1 = Vector2D(1.0, 0.0)
        v2 = Vector2D(0.0, 1.0)
        angle = angle_between(v1, v2)
        assert abs(angle - math.pi / 2) < 1e-9

    def test_same_direction(self):
        v1 = Vector2D(1.0, 0.0)
        v2 = Vector2D(2.0, 0.0)
        angle = angle_between(v1, v2)
        assert abs(angle - 0.0) < 1e-9
