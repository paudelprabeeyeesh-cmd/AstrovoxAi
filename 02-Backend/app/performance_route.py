"""Performance and reliability API routes."""

from __future__ import annotations

import logging
import time
import asyncio
import gc
import tracemalloc
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from app.response_cache_middleware import ResponseCacheMiddleware, cache_invalidation_hooks
from app.query_plan_analyzer import query_plan_analyzer
from app.db_index_recommender import db_index_recommender
from app.stream_buffering import StreamBuffer
from app.backpressure_handler import BackpressureHandler
from app.resource_monitor import resource_monitor
from app.queue_depth_monitor import queue_depth_monitor
from app.cpu_profiler import cpu_profiler
from app.connection_reuse_checker import connection_reuse_checker
from app.memory_leak_detection import memory_leak_detector
from app.batch_processor import BatchProcessor, BatchResult
from app.lazy_loader import get_lazy_module, get_lazy_module_async, get_lazy_module_stats, invalidate_lazy_module, invalidate_all_lazy_modules, register_lazy_module
from app.middleware.security.rate_limit_hardened import get_rate_limiter, RateLimitConfig, DEFAULT_LIMITS
from app.circuit_breaker import circuit_breaker_manager, CircuitBreaker, CircuitState
from app.retry_backoff import RetryWithBackoff, RetryConfig
from app.retry_budget import retry_budget_manager, RetryBudget
from app.cost_management import cost_tracker
from app.cost_estimator import cost_estimator
from app.cost_analysis import cost_analysis_engine, COST_ANALYSIS_TEMPLATES, CostTemplate, CostPeriod
from app.horizontal_scaling import (
    get_gunicorn_config,
    get_scaling_patterns,
    get_scaling_config,
    get_load_balancer_config,
    get_stateless_guidelines,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])


# ============================================================================
# Response Cache
# ============================================================================

class CacheInvalidateRequest(BaseModel):
    path: str = Field(..., description="Path prefix to invalidate")


@router.post("/cache/invalidate")
async def invalidate_cache(request: CacheInvalidateRequest):
    """Invalidate cached responses by path prefix."""
    try:
        from fastapi import Request
        from starlette.middleware.base import BaseHTTPMiddleware
        from app.performance import Cache
        from app.response_cache_middleware import ResponseCacheMiddleware
        middleware = ResponseCacheMiddleware(None)
        middleware.invalidate(request.path)
        return {"status": "invalidated", "path": request.path}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cached responses."""
    try:
        from app.response_cache_middleware import ResponseCacheMiddleware
        middleware = ResponseCacheMiddleware(None)
        middleware.clear()
        return {"status": "cleared"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    try:
        from app.response_cache_middleware import ResponseCacheMiddleware
        middleware = ResponseCacheMiddleware(None)
        stats = middleware.stats
        return {"status": "OK", "stats": stats}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Query Plan Analyzer
# ============================================================================

class AnalyzeQueryRequest(BaseModel):
    query: str = Field(..., description="SQL query to analyze")
    plan: Optional[Dict[str, Any]] = Field(None, description="Query plan JSON")


@router.post("/query/analyze")
async def analyze_query(request: AnalyzeQueryRequest):
    """Analyze a query plan and get index recommendations."""
    try:
        recommendations = db_index_recommender.analyze_query(request.query, request.plan)
        analysis = query_plan_analyzer.analyze(request.plan or {})
        return {
            "status": "OK",
            "recommendations": recommendations,
            "analysis": analysis,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/query/history")
async def query_analysis_history(limit: int = 100):
    """Get query analysis history."""
    try:
        history = query_plan_analyzer.get_history(limit=limit)
        return {"status": "OK", "history": history}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/query/indexes")
async def get_index_recommendations(limit: int = 50):
    """Get accumulated index recommendations."""
    try:
        recs = db_index_recommender.get_recommendations(limit=limit)
        return {"status": "OK", "recommendations": recs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Stream Buffering
# ============================================================================

class StreamBufferRequest(BaseModel):
    buffer_size: int = Field(default=1024 * 1024, description="Buffer size in bytes")
    batch_size: int = Field(default=10, description="Max chunks per batch")
    delimiter: bytes = Field(default=b"\n", description="Line delimiter")


@router.post("/stream/buffer")
async def create_stream_buffer(request: StreamBufferRequest):
    """Create a stream buffer configuration."""
    try:
        buffer = StreamBuffer(
            buffer_size=request.buffer_size,
            batch_size=request.batch_size,
        )
        return {
            "status": "OK",
            "buffer_size": request.buffer_size,
            "batch_size": request.batch_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Backpressure Handler
# ============================================================================

class BackpressureConfig(BaseModel):
    max_concurrency: int = Field(default=10, description="Max concurrent tasks")
    queue_size: int = Field(default=100, description="Max queued tasks")


@router.post("/backpressure/configure")
async def configure_backpressure(config: BackpressureConfig):
    """Configure backpressure handler."""
    try:
        handler = BackpressureHandler(
            max_concurrency=config.max_concurrency,
            queue_size=config.queue_size,
        )
        return {
            "status": "OK",
            "max_concurrency": config.max_concurrency,
            "queue_size": config.queue_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/backpressure/stats")
async def backpressure_stats():
    """Get backpressure handler statistics."""
    try:
        handler = BackpressureHandler()
        return {
            "status": "OK",
            "active": handler.active_count,
            "queued": handler.queued_count,
            "rejected": handler.rejected_count,
            "max_concurrency": handler.max_concurrency,
            "queue_size": handler.queue_size,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Resource Monitor
# ============================================================================

@router.get("/resources/current")
async def resource_current():
    """Get current resource usage snapshot."""
    try:
        snapshot = resource_monitor.get_current()
        return {"status": "OK", "snapshot": snapshot}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/resources/history")
async def resource_history(limit: int = 100):
    """Get resource usage history."""
    try:
        history = resource_monitor.get_history(limit=limit)
        return {"status": "OK", "history": history}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/resources/summary")
async def resource_summary():
    """Get resource usage summary."""
    try:
        summary = resource_monitor.get_summary()
        return {"status": "OK", "summary": summary}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Queue Depth Monitor
# ============================================================================

class QueueRegisterRequest(BaseModel):
    name: str = Field(..., description="Queue name to register")


@router.post("/queue/register")
async def register_queue(request: QueueRegisterRequest):
    """Register a queue for monitoring."""
    try:
        queue_depth_monitor.register_queue(request.name)
        return {"status": "registered", "queue": request.name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/queue/record")
async def record_queue_depth(queue: str, depth: int):
    """Record queue depth for a named queue."""
    try:
        queue_depth_monitor.record(queue, depth)
        return {"status": "recorded", "queue": queue, "depth": depth}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/queue/stats")
async def queue_stats(name: Optional[str] = None):
    """Get queue statistics."""
    try:
        if name:
            stats = queue_depth_monitor.get_stats(name)
            return {"status": "OK", "stats": stats}
        stats = queue_depth_monitor.get_all_stats()
        return {"status": "OK", "stats": stats}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/queue/alerts")
async def queue_alerts(limit: int = 100):
    """Get queue depth alerts."""
    try:
        alerts = queue_depth_monitor.get_alerts(limit=limit)
        return {"status": "OK", "alerts": alerts}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# CPU Profiler
# ============================================================================

@router.post("/profiler/start")
async def profiler_start():
    """Start CPU profiler."""
    try:
        cpu_profiler.start()
        return {"status": "started"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/profiler/stop")
async def profiler_stop(label: str = "default"):
    """Stop CPU profiler and get results."""
    try:
        result = cpu_profiler.stop(label=label)
        return {"status": "stopped", "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/profiler/results")
async def profiler_results(label: str = "default"):
    """Get CPU profiler results."""
    try:
        result = cpu_profiler.get_results(label=label)
        if result is None:
            raise HTTPException(status_code=404, detail="No results for label")
        return {"status": "OK", "result": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/profiler/clear")
async def profiler_clear():
    """Clear CPU profiler results."""
    try:
        cpu_profiler.clear()
        return {"status": "cleared"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Connection Reuse Checker
# ============================================================================

class ConnectionRegisterRequest(BaseModel):
    conn_id: str = Field(..., description="Connection ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Connection metadata")


@router.post("/connections/register")
async def register_connection(request: ConnectionRegisterRequest):
    """Register a connection for tracking."""
    try:
        connection_reuse_checker.register_connection(request.conn_id, None, request.metadata)
        return {"status": "registered", "conn_id": request.conn_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/connections/release")
async def release_connection(conn_id: str):
    """Release a tracked connection."""
    try:
        connection_reuse_checker.release_connection(conn_id)
        return {"status": "released", "conn_id": conn_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/connections/stats")
async def connection_stats():
    """Get connection statistics."""
    try:
        stats = connection_reuse_checker.get_stats()
        return {"status": "OK", "stats": stats}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/connections/leaks")
async def connection_leaks():
    """Check for connection leaks."""
    try:
        leaks = connection_reuse_checker.check_leaks()
        return {"status": "OK", "leaks": leaks, "count": len(leaks)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Memory Leak Detector
# ============================================================================

@router.post("/memory/start")
async def memory_leak_start():
    """Start memory leak detection."""
    try:
        memory_leak_detector.start()
        return {"status": "started"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/memory/stop")
async def memory_leak_stop():
    """Stop memory leak detection."""
    try:
        memory_leak_detector.stop()
        return {"status": "stopped"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/memory/detect")
async def memory_leak_detect(scenario_name: str = "default"):
    """Run memory leak detection for a scenario."""
    try:
        def workload():
            pass
        results = memory_leak_detector.detect(scenario_name, workload)
        return {"status": "OK", "scenario": scenario_name, "leaks": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/memory/snapshot")
async def memory_snapshot():
    """Take a memory snapshot."""
    try:
        snapshot = memory_leak_detector.snapshot()
        return {"status": "OK", "snapshot": "taken"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/memory/compare")
async def memory_compare(before_snapshot_id: str, after_snapshot_id: str, top_n: int = 20):
    """Compare two memory snapshots."""
    try:
        before = memory_leak_detector.get_recorded(before_snapshot_id)
        after = memory_leak_detector.get_recorded(after_snapshot_id)
        if before is None or after is None:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        results = memory_leak_detector.diff(before, after, top_n=top_n)
        return {"status": "OK", "diff": results}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Batch Processor
# ============================================================================

class BatchProcessRequest(BaseModel):
    items: List[Any] = Field(..., description="Items to process")
    batch_size: int = Field(default=100, description="Batch size")
    max_workers: int = Field(default=4, description="Max parallel workers")
    retry_count: int = Field(default=2, description="Retry count per item")


@router.post("/batch/process")
async def batch_process(request: BatchProcessRequest, background_tasks: BackgroundTasks):
    """Process items in batches with retry and progress tracking."""
    try:
        processor = BatchProcessor(
            batch_size=request.batch_size,
            max_workers=request.max_workers,
            retry_count=request.retry_count,
        )

        async def dummy_func(item):
            return item

        result = await processor.process_async(request.items, dummy_func, desc="API batch")
        return {
            "status": "OK",
            "batch_id": result.batch_id,
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "duration_ms": result.duration_ms,
            "errors": result.errors,
            "progress": result.progress,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Lazy Loader
# ============================================================================

class LazyRegisterRequest(BaseModel):
    name: str = Field(..., description="Module name")
    factory: str = Field(..., description="Factory function path")


@router.post("/lazy/register")
async def lazy_register(request: LazyRegisterRequest):
    """Register a lazy-loaded module."""
    try:
        def factory():
            return f"loaded:{request.name}"
        register_lazy_module(request.name, factory)
        return {"status": "registered", "name": request.name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/lazy/get")
async def lazy_get(name: str):
    """Get a lazy-loaded module by name."""
    try:
        value = get_lazy_module(name)
        return {"status": "OK", "name": name, "loaded": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="Module not registered")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/lazy/invalidate")
async def lazy_invalidate(name: Optional[str] = None):
    """Invalidate a lazy-loaded module or all modules."""
    try:
        if name:
            invalidate_lazy_module(name)
            return {"status": "invalidated", "name": name}
        invalidate_all_lazy_modules()
        return {"status": "all_invalidated"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/lazy/stats")
async def lazy_stats():
    """Get lazy loader statistics."""
    try:
        stats = get_lazy_module_stats()
        return {"status": "OK", "stats": stats}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Rate Limiter
# ============================================================================

class RateLimitCheckRequest(BaseModel):
    policy: str = Field(..., description="Rate limit policy name")
    identity: str = Field(..., description="Identity (user ID or IP)")
    amount: int = Field(default=1, description="Request amount")


@router.post("/rate-limit/check")
async def rate_limit_check(request: RateLimitCheckRequest):
    """Check rate limit for a policy and identity."""
    try:
        limiter = get_rate_limiter()
        result = limiter.check(request.policy, request.identity, amount=request.amount)
        return {"status": "OK", "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/rate-limit/policies")
async def rate_limit_policies():
    """List available rate limit policies."""
    try:
        policies = {
            name: {
                "name": cfg.name,
                "requests": cfg.requests,
                "window_seconds": cfg.window_seconds,
                "scope": cfg.scope,
                "burst": cfg.burst,
            }
            for name, cfg in DEFAULT_LIMITS.items()
        }
        return {"status": "OK", "policies": policies}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Circuit Breaker
# ============================================================================

class CircuitBreakerCreateRequest(BaseModel):
    name: str = Field(..., description="Circuit breaker name")
    failure_threshold: int = Field(default=5, description="Failure threshold")
    recovery_timeout: float = Field(default=60.0, description="Recovery timeout seconds")
    half_open_max_calls: int = Field(default=3, description="Max half-open calls")


@router.post("/circuit-breaker/create")
async def create_circuit_breaker(request: CircuitBreakerCreateRequest):
    """Create a circuit breaker."""
    try:
        breaker = CircuitBreaker(
            name=request.name,
            failure_threshold=request.failure_threshold,
            recovery_timeout=request.recovery_timeout,
            half_open_max_calls=request.half_open_max_calls,
        )
        circuit_breaker_manager._breakers[request.name] = breaker
        return {"status": "created", "name": request.name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/circuit-breaker/{name}/success")
async def circuit_breaker_success(name: str):
    """Record a success for a circuit breaker."""
    try:
        breaker = circuit_breaker_manager.get_breaker(name)
        breaker.record_success()
        return {"status": "OK", "name": name, "state": breaker.state.value}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/circuit-breaker/{name}/failure")
async def circuit_breaker_failure(name: str):
    """Record a failure for a circuit breaker."""
    try:
        breaker = circuit_breaker_manager.get_breaker(name)
        breaker.record_failure()
        return {"status": "OK", "name": name, "state": breaker.state.value}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/circuit-breaker/status")
async def circuit_breaker_status():
    """Get status of all circuit breakers."""
    try:
        status = circuit_breaker_manager.get_status()
        return {"status": "OK", "breakers": status}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/circuit-breaker/{name}/can-execute")
async def circuit_breaker_can_execute(name: str):
    """Check if a circuit breaker allows execution."""
    try:
        breaker = circuit_breaker_manager.get_breaker(name)
        allowed = breaker.can_execute()
        return {"status": "OK", "name": name, "allowed": allowed, "state": breaker.state.value}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Retry Budget
# ============================================================================

class RetryBudgetRequest(BaseModel):
    max_retries: int = Field(default=3, description="Max retries")
    initial_delay: float = Field(default=1.0, description="Initial delay seconds")
    max_delay: float = Field(default=60.0, description="Max delay seconds")
    backoff_factor: float = Field(default=2.0, description="Backoff factor")
    jitter: bool = Field(default=True, description="Enable jitter")


@router.post("/retry/execute")
async def retry_execute(func_name: str = "test", config: Optional[RetryBudgetRequest] = None):
    """Execute a test function with retry budget."""
    try:
        cfg = config or RetryBudgetRequest()
        retry_config = RetryConfig(
            max_attempts=cfg.max_retries,
            initial_delay=cfg.initial_delay,
            max_delay=cfg.max_delay,
            backoff_factor=cfg.backoff_factor,
            jitter=cfg.jitter,
        )

        async def test_func():
            return {"result": "success", "func": func_name}

        result = await RetryWithBackoff.execute(test_func, retry_config)
        return {"status": "OK", "result": result, "config": retry_config}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/retry/config")
async def retry_config():
    """Get default retry configuration."""
    try:
        cfg = RetryConfig()
        return {
            "status": "OK",
            "config": {
                "max_attempts": cfg.max_attempts,
                "initial_delay": cfg.initial_delay,
                "max_delay": cfg.max_delay,
                "backoff_factor": cfg.backoff_factor,
                "jitter": cfg.jitter,
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Retry Budget
# ============================================================================

class RetryBudgetCreateRequest(BaseModel):
    name: str = Field(..., description="Budget name")
    max_retries: int = Field(default=100, description="Max retries in window")
    window_seconds: float = Field(default=60.0, description="Window duration")


@router.post("/retry-budget/create")
async def create_retry_budget(request: RetryBudgetCreateRequest):
    """Create a retry budget."""
    try:
        budget = retry_budget_manager.get_budget(
            request.name,
            max_retries=request.max_retries,
            window_seconds=request.window_seconds,
        )
        return {"status": "created", "name": request.name, "stats": budget.get_stats()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/retry-budget/stats")
async def retry_budget_stats(name: Optional[str] = None):
    """Get retry budget statistics."""
    try:
        if name:
            budget = retry_budget_manager.get_budget(name)
            return {"status": "OK", "stats": budget.get_stats()}
        stats = retry_budget_manager.get_all_stats()
        return {"status": "OK", "stats": stats}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/retry-budget/reset")
async def reset_retry_budget(name: str):
    """Reset a retry budget."""
    try:
        budget = retry_budget_manager.get_budget(name)
        budget.reset()
        return {"status": "reset", "name": name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Cost Analysis
# ============================================================================

class CostEstimateRequest(BaseModel):
    model: str = Field(..., description="Model name")
    prompt: str = Field(..., description="Prompt text")
    system_prompt: str = Field(default="", description="System prompt")
    expected_output_tokens: Optional[int] = Field(None, description="Expected output tokens")
    provider: str = Field(default="unknown", description="Provider name")


@router.post("/cost/estimate")
async def cost_estimate(request: CostEstimateRequest):
    """Estimate cost for a request."""
    try:
        estimate = cost_estimator.estimate(
            model=request.model,
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            expected_output_tokens=request.expected_output_tokens,
            provider=request.provider,
        )
        return {
            "status": "OK",
            "estimate": {
                "model": estimate.model,
                "provider": estimate.provider,
                "input_tokens": estimate.input_tokens,
                "output_tokens": estimate.output_tokens,
                "estimated_cost": estimate.estimated_cost,
                "currency": estimate.currency,
                "timestamp": estimate.timestamp,
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cost/report")
async def cost_report(user_id: Optional[str] = None, days: int = 30):
    """Get cost report for a user or globally."""
    try:
        if user_id:
            report = cost_tracker.get_usage_report(user_id, days=days)
        else:
            report = {"period_days": days, "total_requests": 0, "total_cost": 0.0}
        return {"status": "OK", "report": report}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cost/forecast")
async def cost_forecast(user_id: str, days: int = 30):
    """Get cost forecast for a user."""
    try:
        forecast = cost_tracker.get_cost_forecast(user_id, days=days)
        return {"status": "OK", "forecast": forecast}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cost/comparison")
async def cost_comparison(user_id: Optional[str] = None):
    """Get provider cost comparison."""
    try:
        comparison = cost_tracker.get_provider_cost_comparison(user_id=user_id)
        return {"status": "OK", "comparison": comparison}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Cost Analysis Templates
# ============================================================================

@router.get("/cost/templates")
async def list_cost_templates():
    """List available cost analysis templates."""
    try:
        templates = cost_analysis_engine.list_templates()
        return {"status": "OK", "templates": templates}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/cost/analyze")
async def run_cost_analysis(template_name: str = "default", user_id: str = "global", days: int = 30):
    """Run cost analysis using a template."""
    try:
        analysis = cost_analysis_engine.analyze(template_name, user_id, days=days)
        return {"status": "OK", "analysis": analysis}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cost/history")
async def cost_analysis_history(limit: int = 100):
    """Get cost analysis history."""
    try:
        history = cost_analysis_engine.get_history(limit=limit)
        return {"status": "OK", "history": history}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# Horizontal Scaling
# ============================================================================

@router.get("/scaling/gunicorn")
async def scaling_gunicorn():
    """Get Gunicorn configuration for horizontal scaling."""
    try:
        config = get_gunicorn_config()
        return {"status": "OK", "config": config}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/scaling/patterns")
async def scaling_patterns():
    """List available horizontal scaling patterns."""
    try:
        patterns = get_scaling_patterns()
        return {"status": "OK", "patterns": patterns}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/scaling/patterns/{pattern_name}")
async def scaling_pattern_detail(pattern_name: str):
    """Get configuration for a specific scaling pattern."""
    try:
        config = get_scaling_config(pattern_name)
        return {"status": "OK", "pattern": pattern_name, "config": config}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/scaling/load-balancer/{lb_name}")
async def scaling_load_balancer(lb_name: str):
    """Get load balancer configuration."""
    try:
        config = get_load_balancer_config(lb_name)
        return {"status": "OK", "load_balancer": lb_name, "config": config}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/scaling/stateless-guidelines")
async def scaling_stateless_guidelines():
    """Get guidelines for stateless service design."""
    try:
        guidelines = get_stateless_guidelines()
        return {"status": "OK", "guidelines": guidelines}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
