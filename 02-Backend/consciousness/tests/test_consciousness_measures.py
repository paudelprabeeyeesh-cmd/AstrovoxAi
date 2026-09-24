import numpy as np
import pytest

from consciousness.consciousness_measures import ConsciousnessMeasures


def test_mirror_test_passes():
    cm = ConsciousnessMeasures(threshold=0.5)
    r = cm.apply_mirror_test(np.array([1.0]), np.array([1.0]))
    assert r["mirror_test"] == 1.0


def test_mark_test_passes():
    cm = ConsciousnessMeasures(threshold=0.5)
    r = cm.apply_mark_test(np.array([1.0]), np.array([1.0]))
    assert r["mark_test"] == 1.0


def test_report_returns_overall():
    cm = ConsciousnessMeasures()
    cm.apply_mirror_test(np.array([1.0]), np.array([1.0]))
    report = cm.report()
    assert "overall_consciousness" in report
