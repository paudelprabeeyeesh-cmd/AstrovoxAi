from production_readiness.auto_scaling import AutoScaler, ScalingPolicy, MetricsCollector, ScalingMetrics


def test_scaling_policy_defaults():
    policy = ScalingPolicy(name="default")
    assert policy.min_replicas == 1
    assert policy.max_replicas == 20


def test_metrics_collector():
    collector = MetricsCollector()
    avg = collector.average()
    assert avg.cpu == 0.0


def test_auto_scaler_status():
    scaler = AutoScaler()
    policy = ScalingPolicy(name="default")
    scaler.register_policy(policy)
    status = scaler.status()
    assert "default" in status["policies"]


def test_auto_scaler_high_metrics():
    scaler = AutoScaler()
    policy = ScalingPolicy(name="default", target_cpu=10.0, target_memory=10.0, min_replicas=1, max_replicas=10)
    scaler.register_policy(policy)
    scaler.record_metrics("default", ScalingMetrics(cpu=90.0, memory=90.0, requests_per_second=100.0, error_rate=0.0, latency_p99=10.0))
    result = scaler.evaluate("default")
    assert result is not None


def test_auto_scaler_low_metrics():
    scaler = AutoScaler()
    policy = ScalingPolicy(name="default", target_cpu=90.0, target_memory=90.0, min_replicas=0, max_replicas=10, cooldown_seconds=0.0)
    scaler.register_policy(policy)
    scaler.record_metrics("default", ScalingMetrics(cpu=10.0, memory=10.0, requests_per_second=100.0, error_rate=0.0, latency_p99=10.0))
    result = scaler.evaluate("default")
    assert result is None
