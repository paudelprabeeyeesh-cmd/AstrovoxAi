import numpy as np
import pytest

from consciousness.global_workspace import (
    GlobalWorkspace,
    Module,
)


def test_register_module_creates_module():
    gw = GlobalWorkspace()
    m = gw.register_module("m1")
    assert m.name == "m1"
    assert m.activation == 0.0


def test_activate_changes_activation():
    gw = GlobalWorkspace()
    m = gw.activate("m1", 0.8)
    assert m.activation == pytest.approx(0.8)


def test_compete_selects_winners():
    gw = GlobalWorkspace(capacity=2)
    gw.activate("a", 0.9)
    gw.activate("b", 0.4)
    gw.activate("c", 0.3)
    winners = gw.compete()
    assert len(winners) == 2
    assert winners[0].name == "a"


def test_broadcast_returns_queue():
    gw = GlobalWorkspace()
    gw.activate("a", 0.9, content=np.array([1.0, 0.0]))
    queue = gw.broadcast()
    assert len(queue) == 1
    assert queue[0]["norm"] == pytest.approx(1.0)


def test_integrate_merges_modules():
    gw = GlobalWorkspace()
    m1 = gw.register_module("a")
    m1.content = np.array([1.0])
    m2 = Module(name="a", content=np.array([0.0]))
    gw.integrate("a", m2)
    assert gw.modules["a"].content is not None
