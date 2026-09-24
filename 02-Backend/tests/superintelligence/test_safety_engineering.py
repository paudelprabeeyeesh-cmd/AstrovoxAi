import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.safety_engineering import (
    SafetyEngineer,
    ContainmentProtocol,
)


class TestSafetyEngineer:
    def test_add_protocol(self):
        se = SafetyEngineer()
        protocol = se.add_protocol("isolation", strength=0.9, reversibility=0.8, monitoring_coverage=0.95)
        assert isinstance(protocol, ContainmentProtocol)
        assert protocol.name == "isolation"
        assert 0.0 <= protocol.escape_probability <= 1.0

    def test_evaluate_safety_empty(self):
        se = SafetyEngineer()
        result = se.evaluate_safety(capability_level=10.0)
        assert result["safety_score"] == 0.0
        assert result["escape_risk"] == 1.0

    def test_evaluate_safety_with_protocols(self):
        se = SafetyEngineer()
        se.add_protocol("p1", strength=0.9, reversibility=0.8, monitoring_coverage=0.9)
        se.add_protocol("p2", strength=0.85, reversibility=0.7, monitoring_coverage=0.85)
        result = se.evaluate_safety(capability_level=1.0)
        assert result["protocols_active"] == 2
        assert 0.0 <= result["safety_score"] <= 1.0

    def test_shutdown_guarantee_empty(self):
        se = SafetyEngineer()
        result = se.shutdown_guarantee()
        assert result["overall_guarantee"] == 0.0

    def test_shutdown_guarantee_with_protocols(self):
        se = SafetyEngineer()
        se.add_protocol("p1", strength=0.9, reversibility=0.8, monitoring_coverage=0.9)
        result = se.shutdown_guarantee()
        assert result["overall_guarantee"] > 0.0
        assert len(result["protocols"]) == 1

    def test_simulate_escape_attempt(self):
        se = SafetyEngineer()
        se.add_protocol("p1", strength=0.9, reversibility=0.8, monitoring_coverage=0.9)
        result = se.simulate_escape_attempt(capability_level=1.0, n_attempts=200)
        assert result["attempts"] == 200
        assert 0.0 <= result["escape_rate"] <= 1.0

    def test_safety_stats(self):
        se = SafetyEngineer()
        se.add_protocol("p1", strength=0.9, reversibility=0.8, monitoring_coverage=0.9)
        stats = se.get_safety_stats()
        assert stats["protocols"] == 1
        assert stats["mean_strength"] == pytest.approx(0.9)
