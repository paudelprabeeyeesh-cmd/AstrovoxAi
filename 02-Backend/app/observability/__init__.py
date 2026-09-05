"""Enhanced Observability Stack for AstrovoxAi.

Provides:
1. Metrics collection (Prometheus-compatible)
2. Health check system
3. Alerting engine
4. Integration with existing tracing and logging
5. Dashboard and visualization helpers
"""

from __future__ import annotations

import asyncio
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import logging
import json

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Metric:
    """A metric definition."""
    name: str
    type: MetricType
    description: str
    unit: str = ""
    labels: List[str] = field(default_factory=list)


@dataclass
class MetricValue:
    """A metric value with timestamp and labels."""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """A health check definition."""
    name: str
    description: str
    timeout: float = 5.0
    interval: float = 30.0
    critical: bool = False


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """An alert rule definition."""
    name: str
    condition: str  # PromQL-like condition expression
    severity: AlertSeverity
    for_duration: float = 0.0  # How long condition must be true
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """An active alert."""
    rule_name: str
    severity: AlertSeverity
    status: str = "firing"  # firing, resolved
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    starts_at: float = field(default_factory=time.time)
    ends_at: Optional[float] = None


class MetricsCollector:
    """Collects and stores metrics."""

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._summaries: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
        self._metric_definitions: Dict[str, Metric] = {}

    def register_metric(self, metric: Metric):
        """Register a metric definition."""
        with self._lock:
            self._metric_definitions[metric.name] = metric

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter."""
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge value."""
        with self._lock:
            self._gauges[name] = value

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value for a histogram."""
        with self._lock:
            self._histograms[name].append(value)
            # Keep only recent values (last 1000)
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-1000:]

    def observe_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value for a summary."""
        with self._lock:
            self._summaries[name].append(value)
            # Keep only recent values (last 1000)
            if len(self._summaries[name]) > 1000:
                self._summaries[name] = self._summaries[name][-1000:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics in Prometheus format."""
        with self._lock:
            result = {}

            # Counters
            for name, value in self._counters.items():
                result[name] = value

            # Gauges
            for name, value in self._gauges.items():
                result[name] = value

            # Histograms
            for name, values in self._histograms.items():
                if values:
                    sorted_values = sorted(values)
                    n = len(sorted_values)
                    result[f"{name}_count"] = n
                    result[f"{name}_sum"] = sum(sorted_values)
                    result[f"{name}_bucket"] = self._calculate_buckets(sorted_values)

            # Summaries
            for name, values in self._summaries.items():
                if values:
                    sorted_values = sorted(values)
                    n = len(sorted_values)
                    result[f"{name}_count"] = n
                    result[f"{name}_sum"] = sum(sorted_values)
                    result[f"{name}_p50"] = sorted_values[n // 2] if n > 0 else 0
                    result[f"{name}_p95"] = sorted_values[int(n * 0.95)] if n > 0 else 0
                    result[f"{name}_p99"] = sorted_values[int(n * 0.99)] if n > 0 else 0

            return result

    def _calculate_buckets(self, values: List[float]) -> Dict[str, int]:
        """Calculate histogram buckets."""
        # Standard Prometheus buckets
        buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, float('inf')]
        result = {}
        for boundary in buckets:
            if boundary == float('inf'):
                count = len(values)
            else:
                count = sum(1 for v in values if v <= boundary)
            result[f"{boundary}"] = count
        return result


class HealthChecker:
    """Manages health checks."""

    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._results: Dict[str, HealthCheckResult] = {}
        self._lock = threading.RLock()

    def register_check(self, check: HealthCheck):
        """Register a health check."""
        with self._lock:
            self._checks[check.name] = check

    def unregister_check(self, name: str):
        """Unregister a health check."""
        with self._lock:
            self._checks.pop(name, None)
            self._results.pop(name, None)

    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        check = self._checks.get(name)
        if not check:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found"
            )

        start_time = time.time()
        try:
            # In a real implementation, this would call the actual check function
            # For now, we'll simulate a basic check
            await asyncio.sleep(0.01)  # Simulate check execution
            
            # Simulate healthy status for most checks
            status = HealthStatus.HEALTHY
            message = "Check passed"
            
            # Simulate some checks being degraded/unhealthy for demo
            if name == "database" and hash(str(time.time())) % 10 == 0:
                status = HealthStatus.DEGRADED
                message = "Database connection pool at 80% capacity"
            elif name == "external_api" and hash(str(time.time())) % 20 == 0:
                status = HealthStatus.UNHEALTHY
                message = "External API returning 5xx errors"
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                name=name,
                status=status,
                message=message,
                duration_ms=duration_ms
            )
            
            with self._lock:
                self._results[name] = result
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms
            )
            
            with self._lock:
                self._results[name] = result
            
            return result

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        tasks = [self.run_check(name) for name in self._checks.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        check_results = {}
        for i, (name, result) in enumerate(zip(self._checks.keys(), results)):
            if isinstance(result, Exception):
                check_results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check execution failed: {str(result)}"
                )
            else:
                check_results[name] = result
        
        return check_results

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        with self._lock:
            if not self._results:
                return HealthStatus.UNKNOWN
            
            statuses = [result.status for result in self._results.values()]
            
            # If any critical check is unhealthy, system is unhealthy
            for name, result in self._results.items():
                check = self._checks.get(name)
                if check and check.critical and result.status == HealthStatus.UNHEALTHY:
                    return HealthStatus.UNHEALTHY
            
            # If any check is unhealthy, system is degraded
            if any(status == HealthStatus.UNHEALTHY for status in statuses):
                return HealthStatus.DEGRADED
            
            # If any check is degraded, system is degraded
            if any(status == HealthStatus.DEGRADED for status in statuses):
                return HealthStatus.DEGRADED
            
            # If all checks are healthy, system is healthy
            if all(status == HealthStatus.HEALTHY for status in statuses):
                return HealthStatus.HEALTHY
            
            return HealthStatus.UNKNOWN

    def get_last_results(self) -> Dict[str, HealthCheckResult]:
        """Get the last results of all health checks."""
        with self._lock:
            return dict(self._results)


class AlertManager:
    """Manages alert rules and generates alerts."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._lock = threading.RLock()

    def register_rule(self, rule: AlertRule):
        """Register an alert rule."""
        with self._lock:
            self._rules[rule.name] = rule

    def unregister_rule(self, name: str):
        """Unregister an alert rule."""
        with self._lock:
            self._rules.pop(name, None)

    def evaluate_rules(self) -> List[Alert]:
        """Evaluate all alert rules and return new/firing alerts."""
        new_alerts = []
        resolved_alerts = []
        
        with self._lock:
            # Get current metrics
            metrics = self.metrics_collector.get_metrics()
            
            # Evaluate each rule
            for name, rule in self._rules.items():
                # In a real implementation, this would evaluate the condition expression
                # For now, we'll simulate some alerts based on simple conditions
                is_firing = self._evaluate_condition(rule.condition, metrics)
                
                existing_alert = self._active_alerts.get(name)
                
                if is_firing and not existing_alert:
                    # New alert
                    alert = Alert(
                        rule_name=name,
                        severity=rule.severity,
                        labels=rule.labels.copy(),
                        annotations=rule.annotations.copy()
                    )
                    self._active_alerts[name] = alert
                    new_alerts.append(alert)
                    logger.warning(f"Alert fired: {name} ({rule.severity.value})")
                
                elif not is_firing and existing_alert:
                    # Resolve alert
                    existing_alert.status = "resolved"
                    existing_alert.ends_at = time.time()
                    resolved_alerts.append(existing_alert)
                    del self._active_alerts[name]
                    logger.info(f"Alert resolved: {name}")
        
        # Add resolved alerts to history
        self._alert_history.extend(resolved_alerts)
        # Keep only recent history (last 1000 alerts)
        if len(self._alert_history) > 1000:
            self._alert_history = self._alert_history[-1000:]
        
        return new_alerts

    def _evaluate_condition(self, condition: str, metrics: Dict[str, Any]) -> bool:
        """Evaluate an alert condition against current metrics.
        
        This is a simplified implementation. In production, you'd use a proper
        expression parser like Prometheus's.
        """
        # Simple simulation for demonstration
        if "error_rate" in condition and "> 0.05" in condition:
            # Simulate error rate > 5%
            return hash(str(time.time())) % 20 == 0  # 5% chance
        
        if "latency_p95" in condition and "> 8000" in condition:
            # Simulate latency > 8s
            return hash(str(time.time())) % 10 == 0  # 10% chance
        
        if "cpu_usage" in condition and "> 0.8" in condition:
            # Simulate CPU usage > 80%
            return hash(str(time.time())) % 5 == 0  # 20% chance
        
        if "memory_usage" in condition and "> 0.9" in condition:
            # Simulate memory usage > 90%
            return hash(str(time.time())) % 10 == 0  # 10% chance
        
        return False

    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts."""
        with self._lock:
            return list(self._active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        with self._lock:
            return list(self._alert_history[-limit:])

    def silence_alert(self, rule_name: str, duration: float = 300.0):
        """Silence an alert for a duration."""
        # In a full implementation, this would prevent notifications
        logger.info(f"Alert {rule_name} silenced for {duration} seconds")


class ObservabilityStack:
    """Main observability stack integrating metrics, health checks, and alerting."""

    def __init__(self):
        self.metrics = MetricsCollector()
        self.health = HealthChecker()
        self.alerts = AlertManager(self.metrics)
        self._background_tasks: Set[asyncio.Task] = set()
        self._running = False

    async def start(self):
        """Start background tasks for health checks and alert evaluation."""
        if self._running:
            return
        
        self._running = True
        
        # Start health check task
        health_task = asyncio.create_task(self._health_check_loop())
        self._background_tasks.add(health_task)
        health_task.add_done_callback(self._background_tasks.discard)
        
        # Start alert evaluation task
        alert_task = asyncio.create_task(self._alert_evaluation_loop())
        self._background_tasks.add(alert_task)
        alert_task.add_done_callback(self._background_tasks.discard)
        
        logger.info("Observability stack started")

    async def stop(self):
        """Stop background tasks."""
        self._running = False
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()
        logger.info("Observability stack stopped")

    async def _health_check_loop(self):
        """Background loop for running health checks."""
        while self._running:
            try:
                await self.health.run_all_checks()
                # Wait for next interval (use minimum interval from all checks)
                min_interval = 30.0  # Default
                with self.health._lock:
                    for check in self.health._checks.values():
                        min_interval = min(min_interval, check.interval)
                await asyncio.sleep(min_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5.0)  # Back off on error

    async def _alert_evaluation_loop(self):
        """Background loop for evaluating alert rules."""
        while self._running:
            try:
                await self.alerts.evaluate_rules()
                await asyncio.sleep(10.0)  # Evaluate every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert evaluation loop error: {e}")
                await asyncio.sleep(5.0)  # Back off on error

    def get_status(self) -> Dict[str, Any]:
        """Get overall observability status."""
        return {
            "health": {
                "status": self.health.get_overall_status().value,
                "checks": {
                    name: {
                        "status": result.status.value,
                        "message": result.message,
                        "duration_ms": result.duration_ms
                    }
                    for name, result in self.health.get_last_results().items()
                }
            },
            "metrics": {
                "collections": len(self.metrics._metric_definitions),
                "samples": sum(len(v) for v in self.metrics._histograms.values()) +
                          sum(len(v) for v in self.metrics._summaries.values())
            },
            "alerts": {
                "active": len(self.alerts.get_active_alerts()),
                "rules": len(self.alerts._rules),
                "recent": [
                    {
                        "rule_name": alert.rule_name,
                        "severity": alert.severity.value,
                        "status": alert.status,
                        "starts_at": alert.starts_at
                    }
                    for alert in self.alerts.get_alert_history(limit=10)
                ]
            }
        }

    def get_metrics_prometheus(self) -> str:
        """Get metrics in Prometheus format."""
        metrics = self.metrics.get_metrics()
        lines = []
        for name, value in metrics.items():
            if isinstance(value, dict):
                # Handle histogram buckets
                for bucket_key, bucket_value in value.items():
                    lines.append(f"{name}_{bucket_key} {bucket_value}")
            else:
                lines.append(f"{name} {value}")
        return "\n".join(lines)


# Global observability stack instance
observability_stack = ObservabilityStack()

# Convenience functions
def get_observability() -> ObservabilityStack:
    """Get the global observability stack."""
    return observability_stack

def register_metric(metric: Metric):
    """Register a metric with the global observability stack."""
    observability_stack.metrics.register_metric(metric)

def increment_counter(name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
    """Increment a counter metric."""
    observability_stack.metrics.increment(name, value, labels)

def set_gauge(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Set a gauge metric."""
    observability_stack.metrics.set_gauge(name, value, labels)

def observe_histogram(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Observe a value for a histogram metric."""
    observability_stack.metrics.observe_histogram(name, value, labels)

def observe_summary(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Observe a value for a summary metric."""
    observability_stack.metrics.observe_summary(name, value, labels)

def register_health_check(check: HealthCheck):
    """Register a health check."""
    observability_stack.health.register_check(check)

def register_alert_rule(rule: AlertRule):
    """Register an alert rule."""
    observability_stack.alerts.register_rule(rule)

async def start_observability():
    """Start the observability stack."""
    await observability_stack.start()

async def stop_observability():
    """Stop the observability stack."""
    await observability_stack.stop()


# Export for easy access
__all__ = [
    "MetricType",
    "AlertSeverity",
    "HealthStatus",
    "Metric",
    "MetricValue",
    "HealthCheck",
    "HealthCheckResult",
    "AlertRule",
    "Alert",
    "MetricsCollector",
    "HealthChecker",
    "AlertManager",
    "ObservabilityStack",
    "observability_stack",
    "get_observability",
    "register_metric",
    "increment_counter",
    "set_gauge",
    "observe_histogram",
    "observe_summary",
    "register_health_check",
    "register_alert_rule",
    "start_observability",
    "stop_observability"
]