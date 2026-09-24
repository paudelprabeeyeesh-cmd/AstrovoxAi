import numpy as np
import pytest

from consciousness.higher_order import FirstOrderState, MetacognitiveMonitor


def test_monitor_returns_first_order():
    mon = MetacognitiveMonitor()
    fo = mon.monitor(np.array([0.8, 0.2]), source="vision")
    assert fo.confidence >= 0.0


def test_reflect_generates_hot():
    mon = MetacognitiveMonitor()
    fo = mon.monitor(np.array([0.8, 0.2]), source="vision")
    hot = mon.reflect(fo)
    assert hot.level == 2
    assert "knows" in hot.metacognition


def test_confidence_estimate_bounded():
    mon = MetacognitiveMonitor()
    fo = mon.monitor(np.array([0.1, 0.1]), source="vision")
    ce = mon.confidence_estimate(fo)
    assert 0.0 <= ce <= 1.0


def test_introspect_returns_dict():
    mon = MetacognitiveMonitor()
    mon.monitor(np.array([0.5]), source="vision")
    report = mon.introspect()
    assert "mean_confidence" in report
