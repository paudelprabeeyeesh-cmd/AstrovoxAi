import pytest
import numpy as np
from complex_reasoning.spatial_reasoning import SpatialObject, SpatialScene


class TestSpatialObject:
    def test_translate(self):
        obj = SpatialObject("A", position=np.array([1.0, 2.0, 0.0]))
        obj.translate(np.array([1.0, 0.0, 0.0]))
        assert np.allclose(obj.position, np.array([2.0, 2.0, 0.0]))

    def test_rotate(self):
        obj = SpatialObject("A", position=np.array([1.0, 0.0, 0.0]))
        obj.rotate(np.pi / 2, axis=2)
        expected = np.array([0.0, 1.0, 0.0])
        assert np.allclose(obj.position, expected, atol=1e-5)

    def test_distance_to(self):
        a = SpatialObject("A", position=np.array([0.0, 0.0, 0.0]))
        b = SpatialObject("B", position=np.array([3.0, 4.0, 0.0]))
        assert a.distance_to(b) == pytest.approx(5.0)

    def test_contains(self):
        outer = SpatialObject("O", position=np.array([0.0, 0.0, 0.0]), dimensions=np.array([2.0, 2.0, 2.0]))
        inner = SpatialObject("I", position=np.array([0.5, 0.5, 0.5]), dimensions=np.ones(3))
        assert outer.contains(inner)
        outside = SpatialObject("X", position=np.array([5.0, 5.0, 5.0]), dimensions=np.ones(3))
        assert not outer.contains(outside)


class TestSpatialScene:
    def test_add_object(self):
        scene = SpatialScene()
        scene.add_object(SpatialObject("A"))
        assert "A" in scene.objects

    def test_translate_scene(self):
        scene = SpatialScene()
        scene.add_object(SpatialObject("A", position=np.array([1.0, 0.0, 0.0])))
        scene.translate(np.array([1.0, 0.0, 0.0]))
        assert np.allclose(scene.objects["A"].position, np.array([2.0, 0.0, 0.0]))

    def test_rotate_scene(self):
        scene = SpatialScene()
        scene.add_object(SpatialObject("A", position=np.array([1.0, 0.0, 0.0])))
        scene.rotate(np.pi / 2, axis=2)
        assert np.allclose(scene.objects["A"].position, np.array([0.0, 1.0, 0.0]), atol=1e-5)

    def test_distance(self):
        scene = SpatialScene()
        scene.add_object(SpatialObject("A", position=np.array([0.0, 0.0, 0.0])))
        scene.add_object(SpatialObject("B", position=np.array([0.0, 3.0, 0.0])))
        assert scene.distance("A", "B") == pytest.approx(3.0)

    def test_mental_rotation(self):
        scene = SpatialScene()
        scene.add_object(SpatialObject("A", position=np.array([1.0, 0.0, 0.0])))
        delta = scene.mental_rotation("A", np.pi / 2, axis=2)
        assert np.allclose(delta, np.array([-1.0, 1.0, 0.0]), atol=1e-5)

    def test_scene_distance(self):
        scene = SpatialScene()
        scene.add_object(SpatialObject("A", position=np.array([0.0, 0.0, 0.0])))
        scene.add_object(SpatialObject("B", position=np.array([1.0, 0.0, 0.0])))
        d = scene.scene_distance()
        assert d >= 0.0

    def test_topological_relation(self):
        scene = SpatialScene()
        scene.add_object(SpatialObject("A", position=np.array([0.0, 0.0, 0.0])))
        scene.add_object(SpatialObject("B", position=np.array([0.05, 0.0, 0.0])))
        assert scene.topological_relation("A", "B") == "touches"
