"""Performance optimization router for AstrovoxAI backend."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.query_optimizer import query_optimizer
from app.resource_monitor import resource_monitor
from app.database_optimizer import database_optimizer
from app.memory_optimizer import memory_optimizer
from app.cpu_optimizer import cpu_optimizer
from app.load_test import load_tester
from app.benchmark import benchmark
from app.response_cache import response_cache
from app.streaming_optimizer import streaming_optimizer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/performance", tags=["performance"])


class BenchmarkRequest(BaseModel):
    name: str
    iterations: int = Field(default=50, ge=1, le=1000)


class LoadTestRequest(BaseModel):
    endpoint: str = Field(default="health", min_length=1)
    requests: int = Field(default=100, ge=1, le=10000)


@router.get("/stats")
async def get_performance_stats() -> Dict[str, Any]:
    return {
        "query_optimizer": query_optimizer.stats,
        "database_optimizer": database_optimizer.stats,
        "resource_monitor": resource_monitor.get_stats(),
        "memory": memory_optimizer.get_stats_summary(),
        "cpu": cpu_optimizer.get_stats(),
        "response_cache": response_cache.stats(),
        "streaming": {
            "avg_ttft_ms": streaming_optimizer.get_average_ttft(),
            "avg_throughput_tps": streaming_optimizer.get_average_throughput(),
        },
    }


@router.get("/query/slow")
async def get_slow_queries(threshold_ms: float = 100.0) -> Dict[str, Any]:
    return {
        "slow_queries": [
            {
                "query": q.query,
                "execution_time_ms": q.execution_time_ms,
                "rows_returned": q.rows,
                "suggestions": q.suggestions,
            }
            for q in query_optimizer.get_slow_queries()
        ]
    }


@router.get("/query/suggestions")
async def get_query_suggestions() -> Dict[str, Any]:
    return {
        "index_suggestions": query_optimizer.get_index_suggestions(),
        "optimization_suggestions": database_optimizer.get_optimization_suggestions(),
    }


@router.post("/query/profile")
async def profile_query(query: str, execution_time_ms: float, rows_scanned: int = 0, rows_returned: int = 0) -> Dict[str, Any]:
    profile = query_optimizer.profile_query(query, execution_time_ms, rows_scanned, rows_returned)
    return {
        "query_hash": profile.query_hash,
        "execution_time_ms": profile.execution_time_ms,
        "slow": profile.slow,
        "suggestions": profile.suggestions,
    }


@router.get("/memory/trend")
async def get_memory_trend(window_minutes: int = 5) -> Dict[str, Any]:
    return memory_optimizer.get_memory_trend(window_minutes=window_minutes)


@router.post("/memory/gc")
async def trigger_gc(force: bool = False) -> Dict[str, Any]:
    result = memory_optimizer.maybe_gc(force=force)
    return result


@router.get("/memory/stats")
async def get_memory_stats() -> Dict[str, Any]:
    return memory_optimizer.get_stats_summary()


@router.get("/cpu/profile")
async def get_cpu_profile() -> Dict[str, Any]:
    return cpu_optimizer.get_stats()


@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    return response_cache.stats()


@router.post("/cache/invalidate")
async def invalidate_cache(prefix: str) -> Dict[str, Any]:
    count = response_cache.invalidate_prefix(prefix)
    return {"invalidated": count}


@router.post("/benchmark/run")
async def run_benchmark(request: BenchmarkRequest) -> Dict[str, Any]:
    import asyncio

    async def dummy_benchmark():
        await asyncio.sleep(0.001)

    result = await benchmark.benchmark_async(request.name, dummy_benchmark, iterations=request.iterations)
    return {
        "name": result.name,
        "iterations": result.iterations,
        "avg_ms": round(result.avg_time_ms, 3),
        "p95_ms": round(result.p95_time_ms, 3),
        "p99_ms": round(result.p99_time_ms, 3),
        "ops_per_second": round(result.ops_per_second, 2),
    }


@router.get("/benchmark/summary")
async def get_benchmark_summary() -> Dict[str, Any]:
    return benchmark.get_summary()


@router.post("/load-test/run")
async def run_load_test(request: LoadTestRequest) -> Dict[str, Any]:
    if request.endpoint == "health":
        result = load_tester.run_health_load_test(requests=min(request.requests, 1000))
    else:
        result = load_tester.run_chat_load_test()
    return load_tester.to_dict(result)


@router.get("/streaming/metrics")
async def get_streaming_metrics() -> Dict[str, Any]:
    return {
        "avg_ttft_ms": streaming_optimizer.get_average_ttft(),
        "avg_throughput_tps": streaming_optimizer.get_average_throughput(),
    }
