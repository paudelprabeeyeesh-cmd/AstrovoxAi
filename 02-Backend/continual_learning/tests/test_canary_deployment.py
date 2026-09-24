import numpy as np
import pytest
from ..canary_deployment import CanaryDeployment, DeploymentStatus


class TestCanaryDeployment:
    def test_initialization(self):
        cd = CanaryDeployment(
            canary_percentage=0.01,
            error_threshold=0.05,
            latency_threshold_ms=1000.0,
            min_requests=100
        )
        assert cd.canary_percentage == 0.01
        assert cd.error_threshold == 0.05
        assert cd.latency_threshold_ms == 1000.0
        assert cd.min_requests == 100
        assert cd.status == DeploymentStatus.PENDING

    def test_assign_user_canary(self):
        cd = CanaryDeployment(canary_percentage=0.01)
        for i in range(100):
            user_id = f"user_{i}"
            assignment = cd.assign_user(user_id)
            assert assignment in ["canary", "baseline"]

    def test_assign_user_consistency(self):
        cd = CanaryDeployment(canary_percentage=0.01)
        user_id = "test_user_123"
        assignment1 = cd.assign_user(user_id)
        assignment2 = cd.assign_user(user_id)
        assert assignment1 == assignment2

    def test_record_request(self):
        cd = CanaryDeployment(canary_percentage=1.0)
        cd.record_request("user_1", success=True, latency_ms=50.0)
        assert cd.metrics.request_count == 1
        assert cd.metrics.error_count == 0
        assert cd.metrics.avg_latency == 50.0

    def test_record_request_error(self):
        cd = CanaryDeployment(canary_percentage=1.0)
        cd.record_request("user_1", success=False, latency_ms=100.0)
        assert cd.metrics.request_count == 1
        assert cd.metrics.error_count == 1
        assert cd.metrics.error_rate == 1.0

    def test_baseline_requests_ignored(self):
        cd = CanaryDeployment(canary_percentage=0.0)
        cd.record_request("user_1", success=False, latency_ms=100.0)
        assert cd.metrics.request_count == 0

    def test_check_health_insufficient_requests(self):
        cd = CanaryDeployment(min_requests=100)
        cd.record_request("user_1", success=True, latency_ms=50.0)
        health = cd.check_health()

        assert health["healthy"] is False
        assert "Insufficient requests" in health["reason"]

    def test_check_health_error_rate_exceeded(self):
        cd = CanaryDeployment(min_requests=10, error_threshold=0.1, canary_percentage=1.0)
        for i in range(10):
            cd.record_request(f"user_{i}", success=False, latency_ms=50.0)
        health = cd.check_health()

        assert health["healthy"] is False
        assert "Error rate" in health["reason"]

    def test_check_health_latency_exceeded(self):
        cd = CanaryDeployment(min_requests=10, latency_threshold_ms=100.0, canary_percentage=1.0)
        for i in range(10):
            cd.record_request(f"user_{i}", success=True, latency_ms=150.0)
        health = cd.check_health()

        assert health["healthy"] is False
        assert "P99 latency" in health["reason"]

    def test_check_health_healthy(self):
        cd = CanaryDeployment(min_requests=10, error_threshold=0.1, latency_threshold_ms=1000.0, canary_percentage=1.0)
        for i in range(10):
            cd.record_request(f"user_{i}", success=True, latency_ms=50.0)
        health = cd.check_health()

        assert health["healthy"] is True
        assert health["request_count"] == 10
        assert health["error_rate"] == 0.0

    def test_promote_healthy_canary(self):
        cd = CanaryDeployment(min_requests=10, canary_percentage=1.0)
        for i in range(10):
            cd.record_request(f"user_{i}", success=True, latency_ms=50.0)
        cd.promote()
        assert cd.status == DeploymentStatus.COMPLETED

    def test_promote_unhealthy_canary_raises(self):
        cd = CanaryDeployment(min_requests=10, error_threshold=0.0, canary_percentage=1.0)
        for i in range(10):
            cd.record_request(f"user_{i}", success=False, latency_ms=50.0)
        with pytest.raises(RuntimeError, match="Cannot promote unhealthy canary"):
            cd.promote()

    def test_rollback(self):
        cd = CanaryDeployment()
        cd.rollback()
        assert cd.status == DeploymentStatus.ROLLED_BACK
        assert len(cd.issues_detected) == 1
        assert cd.issues_detected[0]["type"] == "rollback"

    def test_simulate_traffic(self):
        cd = CanaryDeployment(canary_percentage=1.0, min_requests=1)
        results = cd.simulate_traffic(100, error_rate=0.02, base_latency_ms=50.0, latency_std=10.0)

        assert results["total_requests"] == 100
        assert cd.metrics.request_count == 100
        assert cd.metrics.avg_latency > 0

    def test_latency_metrics(self):
        cd = CanaryDeployment(canary_percentage=1.0)
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        for i, lat in enumerate(latencies):
            cd.record_request(f"user_{i}", success=True, latency_ms=lat)

        assert np.isclose(cd.metrics.avg_latency, 55.0)
        assert cd.metrics.p99_latency >= 90.0
