import numpy as np
import pytest

from consciousness.self_model import SelfModel


def test_update_changes_identity():
    sm = SelfModel()
    i1 = sm.update(np.array([0.1] * 64))
    assert i1.name == "self"


def test_continuity_between_updates():
    sm = SelfModel()
    sm.update(np.array([0.1] * 64))
    sm.update(np.array([0.1] * 64))
    c = sm.get_continuity()
    assert 0.0 <= c <= 1.0


def test_similarity_to_other():
    sm1 = SelfModel()
    sm2 = SelfModel()
    sm1.update(np.array([0.1] * 64))
    sm2.update(np.array([0.1] * 64))
    score = sm1.similarity_to(sm2)
    assert 0.0 <= score <= 1.0
