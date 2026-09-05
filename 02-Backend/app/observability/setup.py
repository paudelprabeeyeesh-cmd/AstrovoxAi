"""Initialization of the observability stack with default metrics, health checks, and alert rules."""

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
    register_alert_rule
)


def setup_default_observability():
    """Set up default metrics, health checks, and alert rules."""
    obs = get_observability()
    
    # Register default metrics
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
    ]
    
    for metric in default_metrics:
        register_metric(metric)
    
    # Register default health checks
    default_health_checks = [
        HealthCheck(
            name="api",
            description="API service health",
            timeout=5.0,
            interval=30.0,
            critical=True
        ),
        HealthCheck(
            name="database",
            description="Database connectivity",
            timeout=10.0,
            interval=60.0,
            critical=True
        ),
        HealthCheck(
            name="external_api",
            description="External API dependencies",
            timeout=15.0,
            interval=120.0,
            critical=False
        ),
        HealthCheck(
            name="disk_space",
            description="Available disk space",
            timeout=5.0,
            interval=300.0,
            critical=False
        ),
        HealthCheck(
            name="memory_usage",
            description="Memory usage levels",
            timeout=5.0,
            interval=60.0,
            critical=False
        )
    ]
    
    for check in default_health_checks:
        register_health_check(check)
    
    # Register default alert rules
    default_alert_rules = [
        AlertRule(
            name="HighErrorRate",
            condition="rate(http_requests_total{status_code=~\"5..\"}[5m]) > 0.05",
            severity=AlertSeverity.CRITICAL,
            for_duration=120.0,
            labels={"team": "backend"},
            annotations={
                "summary": "High error rate detected",
                "description": "Error rate is above 5% for more than 2 minutes"
            }
        ),
        AlertRule(
            name="HighLatency",
            condition="histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 8",
            severity=AlertSeverity.WARNING,
            for_duration=300.0,
            labels={"team": "backend"},
            annotations={
                "summary": "High latency detected",
                "description": "95th percentile latency is above 8 seconds for more than 5 minutes"
            }
        ),
        AlertRule(
            name="HighCPUUsage",
            condition="process_cpu_usage_ratio > 0.8",
            severity=AlertSeverity.WARNING,
            for_duration=180.0,
            labels={"team": "platform"},
            annotations={
                "summary": "High CPU usage detected",
                "description": "CPU usage is above 80% for more than 3 minutes"
            }
        ),
        AlertRule(
            name="HighMemoryUsage",
            condition="process_memory_usage_bytes / process_max_fds > 0.9",
            severity=AlertSeverity.WARNING,
            for_duration=180.0,
            labels={"team": "platform"},
            annotations={
                "summary": "High memory usage detected",
                "description": "Memory usage is above 90% for more than 3 minutes"
            }
        ),
        AlertRule(
            name="ExecutionFailures",
            condition="rate(astrovoxai_executions_total{status=\"failed\"}[5m]) > 0.1",
            severity=AlertSeverity.ERROR,
            for_duration=120.0,
            labels={"team": "backend"},
            annotations={
                "summary": "High execution failure rate",
                "description": "More than 10% of executions are failing"
            }
        )
    ]
    
    for rule in default_alert_rules:
        register_alert_rule(rule)


# Initialize on import
try:
    setup_default_observability()
    print("Default observability setup completed")
except Exception as e:
    print(f"Failed to setup default observability: {e}")


# Export the setup function
__all__ = ["setup_default_observability"]