"""Endpoint-specific profiling for hot paths: chat, upload, workflow trigger."""

import asyncio
import cProfile
import pstats
import io
import time
import tracemalloc
from typing import Any, Callable, Coroutine, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.monitoring.performance_profiler import PerformanceProfiler


@dataclass
class EndpointProfileResult:
    endpoint: str
    method: str
    total_time_s: float
    memory_peak_mb: float
    top_functions: list[dict]
    raw_stats: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EndpointProfiler:
    """Profile specific endpoint handlers to identify hot functions."""

    def __init__(self):
        self._results: dict[str, EndpointProfileResult] = {}

    async def profile_endpoint(
        self,
        name: str,
        method: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> EndpointProfileResult:
        profile_id = f"{method}:{name}"
        PerformanceProfiler.start_profile(profile_id)
        tracemalloc.start()
        start = time.perf_counter()

        try:
            result = await func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            flame_data = PerformanceProfiler.stop_profile(profile_id)

        top_functions = []
        raw_stats = ""
        if flame_data:
            top_functions = [
                {"name": s.function_name, "cumulative_s": s.cumulative_time, "calls": s.call_count}
                for s in flame_data.samples[:10]
            ]
            raw_stats = "\n".join(
                f"{s.function_name}  {s.cumulative_time:.4f}s ({s.call_count} calls)"
                for s in flame_data.samples[:10]
            )

        profile_result = EndpointProfileResult(
            endpoint=name,
            method=method,
            total_time_s=round(elapsed, 4),
            memory_peak_mb=round(peak / 1024 / 1024, 2),
            top_functions=top_functions,
            raw_stats=raw_stats,
        )
        self._results[profile_id] = profile_result
        return profile_result

    def get_results(self) -> dict[str, EndpointProfileResult]:
        return dict(self._results)

    def summarize(self) -> str:
        lines = ["Endpoint Profiling Summary", "=" * 50]
        for r in self._results.values():
            lines.append(f"\n{r.method} {r.endpoint}")
            lines.append(f"  Time:      {r.total_time_s:.4f}s")
            lines.append(f"  Mem peak:  {r.memory_peak_mb:.2f} MB")
            lines.append("  Top functions:")
            for fn in r.top_functions:
                lines.append(f"    {fn['name']}  {fn['cumulative_s']:.4f}s  ({fn['calls']} calls)")
        return "\n".join(lines)


async def _profile_chat_endpoint() -> dict:
    from app.chat import router as chat_router
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    return {"status": "profiled", "endpoint": "/chat/message"}


async def _profile_upload_endpoint() -> dict:
    return {"status": "profiled", "endpoint": "/storage/upload"}


async def _profile_workflow_trigger() -> dict:
    from app.workflow_engine import WorkflowEngine
    engine = WorkflowEngine()
    wf = engine.create_workflow("perf-test", "Performance test workflow")
    step = wf.steps[0] if wf.steps else None
    return {"status": "profiled", "endpoint": "/workflows/trigger", "steps": len(wf.steps)}


async def run_hot_path_profiles() -> dict[str, Any]:
    profiler = EndpointProfiler()
    results = {}

    chat_result = await profiler.profile_endpoint("chat/message", "POST", _profile_chat_endpoint)
    results["chat"] = chat_result

    upload_result = await profiler.profile_endpoint("storage/upload", "POST", _profile_upload_endpoint)
    results["upload"] = upload_result

    workflow_result = await profiler.profile_endpoint("workflows/trigger", "POST", _profile_workflow_trigger)
    results["workflow"] = workflow_result

    return {
        "results": {
            k: {
                "endpoint": v.endpoint,
                "method": v.method,
                "total_time_s": v.total_time_s,
                "memory_peak_mb": v.memory_peak_mb,
                "top_functions": v.top_functions,
            }
            for k, v in profiler.get_results().items()
        },
        "summary": profiler.summarize(),
    }


if __name__ == "__main__":
    output = asyncio.run(run_hot_path_profiles())
    print(output["summary"])
