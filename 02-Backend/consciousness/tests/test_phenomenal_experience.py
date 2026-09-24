import numpy as np

from consciousness.phenomenal_experience import ExperienceSpace


def test_add_experience_creates_qualia():
    space = ExperienceSpace(dimension=8)
    q = space.add_experience(np.array([0.1] * 8), label="q1")
    assert q.label == "q1"
    assert q.vector.size == 8


def test_similarity_between_experiences():
    space = ExperienceSpace(dimension=8)
    space.add_experience(np.array([0.1] * 8), label="a")
    space.add_experience(np.array([0.1] * 8), label="b")
    score = space.similarity("a", "b")
    assert score > 0.99


def test_relate_returns_array():
    space = ExperienceSpace(dimension=4)
    space.add_experience(np.array([0.1, 0.2, 0.3, 0.4]), label="a")
    space.add_experience(np.array([0.1, 0.2, 0.3, 0.5]), label="b")
    rel = space.relate("a", "differs", "b")
    assert isinstance(rel, np.ndarray)
