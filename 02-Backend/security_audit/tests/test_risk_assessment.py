"""Tests for Task 114: Risk Assessment."""

import numpy as np
import pytest

from security_audit.risk_assessment import (
    RiskControl,
    RiskEngine,
    Threat,
)


@pytest.fixture
def engine():
    return RiskEngine()


class TestThreat:
    def test_threat_creation(self):
        t = Threat("T1", "SQL Injection", "injection", 0.8, 0.9, "SQL attack")
        assert t.likelihood == 0.8
        assert t.impact == 0.9

    def test_threat_defaults(self):
        t = Threat("T2", "XSS", "xss", 0.5, 0.5, "XSS")
        assert t.description == "XSS"


class TestRiskEngine:
    def test_register_threat(self, engine):
        t = Threat("T1", "A", "cat", 0.5, 0.5, "desc")
        engine.register_threat(t)
        assert "T1" in engine._threats

    def test_likelihood_score_bounds(self, engine):
        t = Threat("T1", "A", "cat", 0.5, 0.5, "desc")
        assert 0.0 <= engine.likelihood_score(t) <= 1.0

    def test_impact_score_bounds(self, engine):
        t = Threat("T1", "A", "cat", 0.5, 0.5, "desc")
        assert 0.0 <= engine.impact_score(t) <= 1.0

    def test_raw_risk_product(self, engine):
        t = Threat("T1", "A", "cat", 0.8, 0.9, "desc")
        raw = engine.raw_risk(t)
        assert abs(raw - 0.72) < 0.01

    def test_residual_risk_without_controls(self, engine):
        t = Threat("T1", "A", "cat", 0.8, 0.9, "desc")
        residual = engine.residual_risk(t)
        assert residual == engine.raw_risk(t)

    def test_residual_risk_with_controls(self, engine):
        engine.controls = [RiskControl("firewall", 0.5)]
        t = Threat("T1", "A", "cat", 1.0, 1.0, "desc")
        residual = engine.residual_risk(t)
        assert residual < engine.raw_risk(t)

    def test_score_threat_level_critical(self, engine):
        t = Threat("T1", "A", "cat", 1.0, 1.0, "desc")
        score = engine.score_threat(t)
        assert score.risk_level == "critical"

    def test_score_threat_level_low(self, engine):
        t = Threat("T1", "A", "cat", 0.1, 0.1, "desc")
        score = engine.score_threat(t)
        assert score.risk_level == "low"

    def test_score_threat_level_medium(self, engine):
        t = Threat("T1", "A", "cat", 0.7, 0.5, "desc")
        score = engine.score_threat(t)
        assert score.risk_level == "medium"

    def test_risk_matrix_shape(self, engine):
        engine.register_threat(Threat("T1", "A", "cat", 0.5, 0.5, "d"))
        matrix = engine.risk_matrix()
        assert matrix["matrix"].shape == (5, 5)

    def test_aggregate_risk_empty(self, engine):
        agg = engine.aggregate_risk()
        assert agg["count"] == 0

    def test_aggregate_risk_populated(self, engine):
        engine.register_threat(Threat("T1", "A", "cat", 0.8, 0.9, "d"))
        engine.register_threat(Threat("T2", "B", "cat2", 0.3, 0.2, "d2"))
        agg = engine.aggregate_risk()
        assert agg["count"] == 2
        assert "mean_raw" in agg


class TestRiskAssessmentNumpy:
    def test_risk_scores_numeric(self, engine):
        for i in range(5):
            engine.register_threat(Threat(f"T{i}", f"T{i}", "cat", float(i) / 5.0, 0.5, "d"))
        agg = engine.aggregate_risk()
        assert isinstance(agg["mean_raw"], float)

    def test_matrix_numeric_dtype(self, engine):
        engine.register_threat(Threat("T1", "A", "cat", 0.5, 0.5, "d"))
        matrix = engine.risk_matrix()
        assert matrix["matrix"].dtype in (np.float64, np.float32, np.int64)

    def test_residual_with_multiple_controls(self, engine):
        engine.controls = [RiskControl("c1", 0.3), RiskControl("c2", 0.4)]
        t = Threat("T1", "A", "cat", 1.0, 1.0, "d")
        residual = engine.residual_risk(t)
        assert residual < 1.0

    def test_score_residual_range(self, engine):
        engine.register_threat(Threat("T1", "A", "cat", 0.9, 0.9, "d"))
        score = engine.score_threat(engine._threats["T1"])
        assert 0.0 <= score.residual_score <= 1.0
