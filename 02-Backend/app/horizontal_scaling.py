"""Horizontal scaling examples for AstrovoxAi backend.

This module documents and provides utilities for horizontal scaling patterns:
- Multi-process scaling with Gunicorn
- Kubernetes HPA-based scaling
- Redis-backed session sharing
- Stateless service design
- Load balancer configuration
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# ============================================================================
# Gunicorn Configuration
# ============================================================================

GUNICORN_CONFIG = {
    "workers": int(os.getenv("GUNICORN_WORKERS", "4")),
    "worker_class": "uvicorn.workers.UvicornWorker",
    "bind": "0.0.0.0:8000",
    "max_requests": int(os.getenv("GUNICORN_MAX_REQUESTS", "1000")),
    "max_requests_jitter": int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50")),
    "timeout": int(os.getenv("GUNICORN_TIMEOUT", "30")),
    "keepalive": int(os.getenv("GUNICORN_KEEPALIVE", "2")),
    "accesslog": "-",
    "errorlog": "-",
    "loglevel": os.getenv("LOG_LEVEL", "info"),
}


def get_gunicorn_config() -> Dict[str, Any]:
    """Get Gunicorn configuration for horizontal scaling."""
    return GUNICORN_CONFIG.copy()


# ============================================================================
# Horizontal Scaling Patterns
# ============================================================================

SCALING_PATTERNS: List[Dict[str, Any]] = [
    {
        "name": "vertical_pod_autoscaling",
        "description": "Automatically adjust pod CPU and memory limits",
        "implementation": "kubernetes VPA",
        "benefits": ["Right-sizing", "Cost optimization", "Auto-tuning"],
        "config": {
            "min_cpu": "500m",
            "max_cpu": "4000m",
            "min_memory": "512Mi",
            "max_memory": "4Gi",
        }
    },
    {
        "name": "horizontal_pod_autoscaling",
        "description": "Scale pod count based on metrics",
        "implementation": "kubernetes HPA",
        "benefits": ["Elastic scaling", "Load-based", "Multi-metric"],
        "config": {
            "min_replicas": 3,
            "max_replicas": 100,
            "target_cpu_utilization": 70,
            "target_memory_utilization": 75,
        }
    },
    {
        "name": "cluster_autoscaling",
        "description": "Add/remove nodes based on pending pods",
        "implementation": "kubernetes CA",
        "benefits": ["Node-level scaling", "Cost-effective", "Multi-tenant"],
        "config": {
            "min_nodes": 3,
            "max_nodes": 50,
            "scale_down_delay": "10m",
        }
    },
    {
        "name": "connection_pooling",
        "description": "Share database connections across workers",
        "implementation": "SQLAlchemy + PgBouncer",
        "benefits": ["Reduced connection overhead", "Better resource utilization"],
        "config": {
            "pool_size": 20,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600,
        }
    },
    {
        "name": "redis_cluster",
        "description": "Distributed caching with Redis Cluster",
        "implementation": "Redis Cluster with sharding",
        "benefits": ["High availability", "Linear scalability", "Low latency"],
        "config": {
            "shards": 6,
            "replicas_per_shard": 1,
            "max_memory": "4GB",
            "eviction_policy": "allkeys-lru",
        }
    },
    {
        "name": "read_replicas",
        "description": "Scale database reads with read replicas",
        "implementation": "PostgreSQL streaming replication",
        "benefits": ["Read scalability", "High availability", "Geographic distribution"],
        "config": {
            "primary": 1,
            "replicas": 3,
            "replication_lag_threshold": "1s",
        }
    },
]


def get_scaling_patterns() -> List[Dict[str, Any]]:
    """Get available horizontal scaling patterns."""
    return SCALING_PATTERNS


def get_scaling_config(pattern_name: str) -> Dict[str, Any]:
    """Get configuration for a specific scaling pattern."""
    for pattern in SCALING_PATTERNS:
        if pattern["name"] == pattern_name:
            return pattern["config"]
    raise ValueError(f"Unknown scaling pattern: {pattern_name}")


# ============================================================================
# Load Balancer Configuration
# ============================================================================

LOAD_BALANCER_CONFIGS = {
    "nginx": {
        "upstream_backend": "astrovox_backend",
        "servers": ["127.0.0.1:8000", "127.0.0.1:8001", "127.0.0.1:8002"],
        "lb_method": "least_conn",
        "keepalive": 32,
        "proxy_read_timeout": "30s",
        "proxy_send_timeout": "30s",
        "proxy_connect_timeout": "5s",
    },
    "traefik": {
        "entrypoints": ["web"],
        "backend": "astrovox-backend",
        "load_balancer": {
            "method": "drr",
            "pass_host_header": True,
        },
        "healthcheck": {
            "scheme": "http",
            "path": "/health/live",
            "interval": "10s",
            "timeout": "2s",
        }
    },
}


def get_load_balancer_config(lb_name: str) -> Dict[str, Any]:
    """Get load balancer configuration."""
    if lb_name not in LOAD_BALANCER_CONFIGS:
        raise ValueError(f"Unknown load balancer: {lb_name}")
    return LOAD_BALANCER_CONFIGS[lb_name]


# ============================================================================
# Stateless Service Design
# ============================================================================

STATELESS_GUIDELINES = [
    "Store session state in Redis or database, not in-process",
    "Use JWT tokens for authentication instead of server-side sessions",
    "Make all API endpoints idempotent where possible",
    "Use background task queues (Celery/ARQ) for async work",
    "Share static assets via CDN",
    "Use database for persistent state",
    "Implement graceful shutdown with connection draining",
    "Use health checks for load balancer integration",
]


def get_stateless_guidelines() -> List[str]:
    """Get guidelines for stateless service design."""
    return STATELESS_GUIDELINES.copy()
