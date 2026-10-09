import numpy as np
import pytest

from consciousness.integrated_information import SystemModel, compute_phi


def test_stationary_distribution_sums_to_one():
    sm = SystemModel(3)
    s = sm.stationary()
    assert s.sum() == pytest.approx(1.0)


def test_transition_preserves_sum():
    sm = SystemModel(2)
    state = np.array([0.5, 0.5])
    ns = sm.transition(state)
    assert ns.sum() == pytest.approx(1.0)


def test_step_near_stationary():
    sm = SystemModel(2)
    s = np.array([1.0, 0.0])
    ns = sm.step(s, steps=50)
    assert ns.sum() == pytest.approx(1.0)


def test_compute_phi_non_negative():
    sm = SystemModel(2)
    phi = compute_phi(sm)
    assert phi >= 0.0


def test_cause_effect_structure_returns_dict():
    sm = SystemModel(2)
    res = sm.cause_effect_structure(np.array([True, False]))
    assert "cause" in res and "effect" in res
