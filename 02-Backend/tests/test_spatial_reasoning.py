import pytest
import numpy as np
from world_model.spatial_reasoning import SpatialReasoner, Pose3D, SpatialGraph


class TestPose3D:
    def test_to_matrix_shape(self):
        pose = Pose3D(x=1.0, y=2.0, z=3.0)
        m = pose.to_matrix()
        assert m.shape == (4, 4)

    def test_transform_point(self):
        pose = Pose3D(x=1.0, y=0.0, z=0.0)
        p = np.array([0.0, 0.0, 0.0])
        result = pose.transform_point(p)
        assert np.allclose(result, np.array([1.0, 0.0, 0.0]), atol=1e-5)


class TestSpatialGraph:
    def test_shortest_path(self):
        g = SpatialGraph()
        g.add_node("a", Pose3D())
        g.add_node("b", Pose3D())
        g.add_node("c", Pose3D())
        g.add_edge("a", "b", 1.0)
        g.add_edge("b", "c", 1.0)
        path = g.shortest_path("a", "c")
        assert path == ["a", "b", "c"]

    def test_distance(self):
        g = SpatialGraph()
        g.add_node("a", Pose3D(x=0.0, y=0.0, z=0.0))
        g.add_node("b", Pose3D(x=3.0, y=4.0, z=0.0))
        assert g.distance("a", "b") == pytest.approx(5.0)

    def test_no_path_returns_none(self):
        g = SpatialGraph()
        g.add_node("a", Pose3D())
        g.add_node("b", Pose3D())
        assert g.shortest_path("a", "b") is None


class TestSpatialReasoner:
    def test_register_object(self):
        r = SpatialReasoner()
        r.register_object("box", np.array([1.0, 2.0, 0.0]))
        assert "box" in r.graph.nodes

    def test_line_of_sight_blocked(self):
        r = SpatialReasoner()
        r.register_object("a", np.array([0.0, 0.0, 0.0]))
        r.register_object("b", np.array([2.0, 0.0, 0.0]))
        r.register_obstacle(np.array([1.0, 0.0, 0.0]), radius=1.0)
        assert not r.line_of_sight("a", "b")

    def test_line_of_sight_clear(self):
        r = SpatialReasoner()
        r.register_object("a", np.array([0.0, 0.0, 0.0]))
        r.register_object("b", np.array([2.0, 0.0, 0.0]))
        r.register_obstacle(np.array([5.0, 0.0, 0.0]), radius=1.0)
        assert r.line_of_sight("a", "b")
