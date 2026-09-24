import pytest
from production_readiness.canary_analysis import CanaryAnalysis, CanaryRegistry, CanaryDeployment


def test_canary_deploy():
    ca = CanaryAnalysis()
    deployment = ca.deploy("v2.0.0", 0.1, 3)
    assert deployment.version == "v2.0.0"
    assert deployment.traffic_percentage == 0.1


def test_canary_promote():
    ca = CanaryAnalysis()
    deployment = ca.deploy("v2.0.0", 0.1, 3)
    result = ca.promote(deployment.id)
    assert result["promoted"] is True
    assert deployment.traffic_percentage == 100.0


def test_canary_rollback():
    ca = CanaryAnalysis()
    deployment = ca.deploy("v2.0.0", 0.1, 3)
    result = ca.rollback(deployment.id)
    assert result["rolled_back"] is True
    assert deployment.healthy is False
    assert deployment.traffic_percentage == 0.0


def test_canary_analyze_healthy():
    ca = CanaryAnalysis()
    deployment = ca.deploy("v2.0.0", 0.1, 3)
    deployment.error_rate = 0.01
    deployment.latency_p99 = 100.0
    analysis = ca.analyze(deployment.id)
    assert analysis["healthy"] is True


def test_canary_analyze_unhealthy():
    ca = CanaryAnalysis()
    deployment = ca.deploy("v2.0.0", 0.1, 3)
    deployment.error_rate = 0.5
    deployment.latency_p99 = 1000.0
    analysis = ca.analyze(deployment.id)
    assert analysis["healthy"] is False
