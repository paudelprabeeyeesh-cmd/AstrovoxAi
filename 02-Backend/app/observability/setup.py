"""Initialization of the observability stack with default metrics, health checks, alert rules, and new modules."""

from __future__ import annotations

import asyncio
from app.observability import (
    get_observability,
    Metric,
    MetricType,
    HealthCheck,
    AlertRule,
    AlertSeverity,
    register_metric,
    register_health_check,
    register_alert_rule,
    log_retention,
    sampler,
    cost_tracker,
    error_budget_dashboard,
    oncall,
    usage_analytics,
    IncidentTimelineVisualizer,
)


def setup_default_observability():
    """Set up default metrics, health checks, alert rules, and new observability modules."""
    obs = get_observability()

    default_metrics = [
        Metric("http_requests_total", MetricType.COUNTER, "Total HTTP requests", "requests", ["method", "endpoint", "status_code"]),
        Metric("http_request_duration_seconds", MetricType.HISTOGRAM, "HTTP request duration in seconds", "seconds", ["method", "endpoint"]),
        Metric("astrovoxai_executions_total", MetricType.COUNTER, "Total DSL executions", "executions", ["status", "type"]),
        Metric("astrovoxai_execution_duration_seconds", MetricType.HISTOGRAM, "DSL execution duration in seconds", "seconds", ["type"]),
        Metric("astrovoxai_memory_operations_total", MetricType.COUNTER, "Total memory operations", "operations", ["operation_type", "status"]),
        Metric("astrovoxai_agent_actions_total", MetricType.COUNTER, "Total agent actions", "actions", ["agent_id", "action_type", "status"]),
        Metric("process_cpu_usage_ratio", MetricType.GAUGE, "Process CPU usage ratio", "ratio"),
        Metric("process_memory_usage_bytes", MetricType.GAUGE, "Process memory usage in bytes", "bytes"),
        Metric("process_open_fds", MetricType.GAUGE, "Number of open file descriptors", "fds"),
        Metric("process_max_fds", MetricType.GAUGE, "Maximum number of file descriptors", "fds"),
        Metric("ai_requests_total", MetricType.COUNTER, "Total AI API requests", "requests", ["model", "status"]),
        Metric("ai_tokens_total", MetricType.COUNTER, "Total AI tokens consumed", "tokens", ["model"]),
        Metric("ai_cost_usd_total", MetricType.COUNTER, "Total AI cost in USD", "usd", ["model", "user_tier"]),
        Metric("active_users", MetricType.GAUGE, "Number of active users", "users"),
        Metric("error_budget_remaining", MetricType.GAUGE, "Error budget remaining", "ratio", ["slo_name"]),
        Metric("error_budget_consumed_pct", MetricType.GAUGE, "Error budget consumed percentage", "percent", ["slo_name"]),
        Metric("incidents_total", MetricType.COUNTER, "Total incidents", "incidents", ["severity", "status"]),
        Metric("cache_hits_total", MetricType.COUNTER, "Total cache hits", "hits", ["backend_type"]),
        Metric("cache_misses_total", MetricType.COUNTER, "Total cache misses", "misses", ["backend_type"]),
    ]

    for metric in default_metrics:
        register_metric(metric)

    default_health_checks = [
        HealthCheck(name="api", description="API service health", timeout=5.0, interval=30.0, critical=True),
        HealthCheck(name="database", description="Database connectivity", timeout=10.0, interval=60.0, critical=True),
        HealthCheck(name="external_api", description="External API dependencies", timeout=15.0, interval=120.0, critical=False),
        HealthCheck(name="disk_space", description="Available disk space", timeout=5.0, interval=300.0, critical=False),
        HealthCheck(name="memory_usage", description="Memory usage levels", timeout=5.0, interval=60.0, critical=False),
        HealthCheck(name="llm_providers", description="LLM provider connectivity", timeout=15.0, interval=120.0, critical=False),
        HealthCheck(name="cache", description="Cache backend connectivity", timeout=5.0, interval=60.0, critical=False),
    ]

    for check in default_health_checks:
        register_health_check(check)

    default_alert_rules = [
        AlertRule(
            name="HighErrorRate",
            condition="rate(http_requests_total{status_code=~\"5..\"}[5m]) > 0.05",
            severity=AlertSeverity.CRITICAL,
            for_duration=120.0,
            labels={"team": "backend"},
            annotations={"summary": "High error rate detected", "description": "Error rate is above 5% for more than 2 minutes"},
        ),
        AlertRule(
            name="HighLatency",
            condition="histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 8",
            severity=AlertSeverity.WARNING,
            for_duration=300.0,
            labels={"team": "backend"},
            annotations={"summary": "High latency detected", "description": "P95 latency is above 8 seconds for more than 5 minutes"},
        ),
        AlertRule(
            name="HighCPUUsage",
            condition="process_cpu_usage_ratio > 0.8",
            severity=AlertSeverity.WARNING,
            for_duration=180.0,
            labels={"team": "platform"},
            annotations={"summary": "High CPU usage detected", "description": "CPU usage is above 80% for more than 3 minutes"},
        ),
        AlertRule(
            name="HighMemoryUsage",
            condition="process_memory_usage_bytes / process_max_fds > 0.9",
            severity=AlertSeverity.WARNING,
            for_duration=180.0,
            labels={"team": "platform"},
            annotations={"summary": "High memory usage detected", "description": "Memory usage is above 90% for more than 3 minutes"},
        ),
        AlertRule(
            name="ExecutionFailures",
            condition="rate(astrovoxai_executions_total{status=\"failed\"}[5m]) > 0.1",
            severity=AlertSeverity.ERROR,
            for_duration=120.0,
            labels={"team": "backend"},
            annotations={"summary": "High execution failure rate", "description": "More than 10% of executions are failing"},
        ),
        AlertRule(
            name="AIHighErrorRate",
            condition="rate(ai_requests_total{status=\"error\"}[5m]) / rate(ai_requests_total[5m]) > 0.1",
            severity=AlertSeverity.ERROR,
            for_duration=120.0,
            labels={"team": "ai"},
            annotations={"summary": "High AI error rate", "description": "AI error rate above 10%"},
        ),
        AlertRule(
            name="CacheHitRateLow",
            condition="rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.5",
            severity=AlertSeverity.WARNING,
            for_duration=300.0,
            labels={"team": "platform"},
            annotations={"summary": "Cache hit rate low", "description": "Cache hit rate below 50%"},
        ),
    ]

    for rule in default_alert_rules:
        register_alert_rule(rule)

    log_retention.add_rule(LogRetentionPolicy.RetentionRule(
        rule_id="default-log-7d",
        name="Default 7-day logs",
        pattern="*.log",
        retention_days=7,
        action=log_retention.RetentionAction.COMPRESS,
    ))
    log_retention.add_rule(LogRetentionPolicy.RetentionRule(
        rule_id="default-log-30d",
        name="Default 30-day logs",
        pattern="*.log.gz",
        retention_days=30,
        action=log_retention.RetentionAction.DELETE,
    ))

    sampler.set_strategy(sampler.SamplingStrategy.PROBABILISTIC, probability=0.1)
    sampler.add_custom_rule(lambda attrs: 1.0 if attrs.get("severity") == "critical" else 0.0)

    for rotation_name, member_ids in [
        ("backend-primary", ["user-1", "user-2", "user-3"]),
        ("ai-primary", ["user-4", "user-5"]),
    ]:
        oncall.register_rotation(oncall.RotationSchedule(
            rotation_id=rotation_name,
            name=rotation_name,
            members=member_ids,
            start_date=asyncio.get_event_loop().time() if hasattr(asyncio, "get_event_loop") else __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            rotation_days=7,
        ))

    cost_tracker.set_budget("ai-service", daily_usd=500.0, monthly_usd=10000.0)
    cost_tracker.set_budget("embedding-service", daily_usd=100.0, monthly_usd=2000.0)

    error_budget_dashboard.record_snapshot(error_budget_dashboard.ErrorBudgetSnapshot(
        slo_name="api_availability",
        target_slo=0.999,
        window_days=30,
        error_budget_total=0.001,
        error_budget_remaining=0.001,
        error_budget_consumed_pct=0.0,
        burn_rate_per_hour=0.0,
        projected_exhaustion_days=None,
        compliance_pct=99.9,
    ))

    IncidentTimelineVisualizer.create_incident(
        title="Observability stack initialized",
        severity=oncall.IncidentSeverity.P4_LOW,
        description="Initial system health check",
        affected_services=["observability"],
        owner="system",
        tags=["system", "bootstrap"],
    )


try:
    setup_default_observability()
except Exception as e:
    print(f"Failed to setup default observability: {e}")


__all__ = ["setup_default_observability"]
