import numpy as np

from consciousness.temporal_awareness import TemporalAwareness


def test_update_returns_moment():
    ta = TemporalAwareness()
    m = ta.update(np.array([0.1, 0.2]), 0.0)
    assert m.timestamp == 0.0


def test_duration_zero_for_empty():
    ta = TemporalAwareness()
    assert ta.duration() == 0.0


def test_flow_non_negative():
    ta = TemporalAwareness()
    ta.update(np.array([0.1]), 0.0)
    ta.update(np.array([0.2]), 0.1)
    assert ta.flow() >= 0.0
