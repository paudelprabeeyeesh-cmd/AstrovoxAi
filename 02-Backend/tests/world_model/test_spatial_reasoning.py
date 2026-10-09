import unittest

import numpy as np

from world_model.spatial_reasoning import Pose3D, SpatialGraph, SpatialReasoner


class TestPose3D(unittest.TestCase):
    def test_defaults(self):
        pose = Pose3D()
        self.assertEqual(pose.x, 0.0)
        self.assertEqual(pose.y, 0.0)
        self.assertEqual(pose.z, 0.0)

    def test_to_matrix(self):
        pose = Pose3D(x=1.0, y=2.0, z=3.0)
        m = pose.to_matrix()
        self.assertEqual(m.shape, (4, 4))
        self.assertAlmostEqual(m[0, 3], 1.0)
        self.assertAlmostEqual(m[1, 3], 2.0)
        self.assertAlmostEqual(m[2, 3], 3.0)

    def test_transform_point(self):
        pose = Pose3D(x=1.0, y=0.0, z=0.0)
        p = np.array([0.0, 0.0, 0.0])
        result = pose.transform_point(p)
        self.assertAlmostEqual(result[0], 1.0)


class TestSpatialGraph(unittest.TestCase):
    def test_add_node(self):
        g = SpatialGraph()
        g.add_node("n1", Pose3D())
        self.assertIn("n1", g.nodes)

    def test_add_edge(self):
        g = SpatialGraph()
        g.add_node("n1", Pose3D())
        g.add_node("n2", Pose3D())
        g.add_edge("n1", "n2", 1.0)
        self.assertEqual(len(g.edges), 1)

    def test_shortest_path_basic(self):
        g = SpatialGraph()
        g.add_node("a", Pose3D())
        g.add_node("b", Pose3D())
        g.add_node("c", Pose3D())
        g.add_edge("a", "b", 1.0)
        g.add_edge("b", "c", 1.0)
        path = g.shortest_path("a", "c")
        self.assertEqual(path, ["a", "b", "c"])

    def test_shortest_path_none(self):
        g = SpatialGraph()
        g.add_node("a", Pose3D())
        result = g.shortest_path("a", "b")
        self.assertIsNone(result)

    def test_distance(self):
        g = SpatialGraph()
        g.add_node("a", Pose3D(x=0.0, y=0.0, z=0.0))
        g.add_node("b", Pose3D(x=3.0, y=4.0, z=0.0))
        d = g.distance("a", "b")
        self.assertAlmostEqual(d, 5.0)

    def test_distance_missing_node(self):
        g = SpatialGraph()
        self.assertEqual(g.distance("a", "b"), float("inf"))


class TestSpatialReasoner(unittest.TestCase):
    def test_register_object(self):
        r = SpatialReasoner()
        r.register_object("o1", np.array([0.0, 0.0, 0.0]))
        self.assertIn("o1", r.graph.nodes)

    def test_register_obstacle(self):
        r = SpatialReasoner()
        r.register_obstacle(np.array([0.0, 0.0, 0.0]), radius=1.0)
        self.assertEqual(len(r.obstacles), 1)

    def test_navigate(self):
        r = SpatialReasoner()
        r.register_object("a", np.array([0.0, 0.0, 0.0]))
        r.register_object("b", np.array([1.0, 0.0, 0.0]))
        r.graph.add_edge("a", "b", 1.0)
        path = r.navigate("a", "b")
        self.assertEqual(path, ["a", "b"])

    def test_line_of_sight_clear(self):
        r = SpatialReasoner()
        r.register_object("a", np.array([0.0, 0.0, 0.0]))
        r.register_object("b", np.array([10.0, 0.0, 0.0]))
        self.assertTrue(r.line_of_sight("a", "b"))

    def test_line_of_sight_blocked(self):
        r = SpatialReasoner()
        r.register_object("a", np.array([0.0, 0.0, 0.0]))
        r.register_object("b", np.array([2.0, 0.0, 0.0]))
        r.register_obstacle(np.array([1.0, 0.0, 0.0]), radius=2.0)
        self.assertFalse(r.line_of_sight("a", "b"))


if __name__ == "__main__":
    unittest.main()
