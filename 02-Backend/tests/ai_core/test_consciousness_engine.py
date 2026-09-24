import numpy as np
from ai_core.consciousness_engine import ConsciousnessEngine, GlobalWorkspace, IntegratedInformationCalculator, ContentElement


def test_global_workspace_compete():
    gw = GlobalWorkspace(capacity=4, competition_threshold=0.5)
    candidates = [
        ContentElement(content="a", activation=0.9, source_module="m1"),
        ContentElement(content="b", activation=0.2, source_module="m2"),
        ContentElement(content="c", activation=0.8, source_module="m3"),
    ]
    winners = gw.compete(candidates)
    assert all(c.activation >= 0.0 for c in winners)
    assert len(winners) <= 4


def test_integrated_information_phi():
    calc = IntegratedInformationCalculator()
    elements = np.array([0.5, 0.7, 0.3])
    connectivity = np.eye(3)
    phi = calc.compute_phi(elements, connectivity)
    assert phi >= 0.0


def test_integrated_information_partition():
    calc = IntegratedInformationCalculator()
    elements = np.array([0.5, 0.7, 0.3, 0.1])
    info = calc.partition_info(elements, parts=2)
    assert "phi_full" in info
    assert "phi_partitioned" in info
    assert "loss" in info


def test_consciousness_engine_update():
    engine = ConsciousnessEngine(capacity=8)
    inputs = [
        ContentElement(content="thought1", activation=0.9, source_module="reasoning"),
        ContentElement(content="thought2", activation=0.5, source_module="memory"),
    ]
    state = engine.update(inputs)
    assert "awareness_level" in state
    assert "phi" in state
    assert state["broadcast_count"] <= 8


def test_consciousness_metrics():
    engine = ConsciousnessEngine()
    assert engine.get_consciousness_metrics()["status"] == "no_data"
    inputs = [ContentElement(content="x", activation=0.6, source_module="test")]
    engine.update(inputs)
    metrics = engine.get_consciousness_metrics()
    assert metrics["total_updates"] == 1
