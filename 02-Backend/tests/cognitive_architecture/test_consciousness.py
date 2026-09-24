import numpy as np
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.consciousness import (
    GlobalWorkspace,
    IntegratedInformationCalculator,
    ConsciousnessMonitor,
    ContentElement,
)


class TestGlobalWorkspace:
    def test_compete_selects_high_activation(self):
        gw = GlobalWorkspace(capacity=4, competition_threshold=0.1)
        elements = [
            ContentElement(content="low", activation=0.1, source_module="a"),
            ContentElement(content="high", activation=0.9, source_module="b"),
        ]
        winners = gw.compete(elements)
        assert any(e.content == "high" for e in winners)

    def test_broadcast_adds_to_workspace(self):
        gw = GlobalWorkspace(capacity=4)
        elements = [ContentElement(content="x", activation=1.0, source_module="a")]
        gw.broadcast(elements)
        assert len(gw._workspace) == 1

    def test_capacity_limit(self):
        gw = GlobalWorkspace(capacity=2)
        for i in range(5):
            gw.broadcast([ContentElement(content=f"c{i}", activation=float(i), source_module="a")])
        assert len(gw._workspace) <= 2

    def test_get_current_contents(self):
        gw = GlobalWorkspace(capacity=4)
        gw.broadcast([ContentElement(content="test", activation=0.8, source_module="mod")])
        contents = gw.get_current_contents()
        assert len(contents) == 1
        assert contents[0]["content"] == "test"


class TestIntegratedInformationCalculator:
    def test_phi_zero_for_empty(self):
        calc = IntegratedInformationCalculator()
        phi = calc.compute_phi(np.array([]), np.array([]))
        assert phi == 0.0

    def test_phi_positive_for_correlated(self):
        calc = IntegratedInformationCalculator()
        x = np.random.randn(32)
        connectivity = np.eye(32)
        phi = calc.compute_phi(x, connectivity)
        assert phi >= 0.0

    def test_partition_info(self):
        calc = IntegratedInformationCalculator()
        x = np.random.randn(16)
        result = calc.partition_info(x, parts=2)
        assert "phi_full" in result
        assert "phi_partitioned" in result
        assert "loss" in result

    def test_loss_positive(self):
        calc = IntegratedInformationCalculator()
        x = np.random.randn(16)
        result = calc.partition_info(x, parts=2)
        assert result["loss"] >= 0.0


class TestConsciousnessMonitor:
    def test_update_with_inputs(self):
        cm = ConsciousnessMonitor(capacity=8)
        inputs = [ContentElement(content=f"c{i}", activation=float(i), source_module=f"m{i}") for i in range(4)]
        state = cm.update(inputs)
        assert "awareness_level" in state
        assert "phi" in state

    def test_empty_inputs(self):
        cm = ConsciousnessMonitor(capacity=8)
        state = cm.update([])
        assert "awareness_level" in state

    def test_get_awareness_level(self):
        cm = ConsciousnessMonitor(capacity=8)
        inputs = [ContentElement(content="x", activation=1.0, source_module="a")]
        cm.update(inputs)
        level = cm.get_awareness_level()
        assert level >= 0.0

    def test_consciousness_metrics_no_data(self):
        cm = ConsciousnessMonitor()
        metrics = cm.get_consciousness_metrics()
        assert metrics["status"] == "no_data"

    def test_consciousness_metrics_after_update(self):
        cm = ConsciousnessMonitor(capacity=8)
        inputs = [ContentElement(content="x", activation=0.5, source_module="a")]
        cm.update(inputs)
        metrics = cm.get_consciousness_metrics()
        assert metrics["total_updates"] == 1
