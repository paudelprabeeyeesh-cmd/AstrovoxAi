
import time
import numpy as np

from inference_engine.latency_profiler import (
    LatencyProfiler,
    LatencyEvent,
    LatencyEventType, ProfilingContext,
)


def _fixed_event(
    event_type: LatencyEventType,
    latency_ms: float,
    tokens: int = 0,
) -> LatencyEvent:
    return LatencyEvent(
        event_type=event_type,
        latency_ms=latency_ms,
        tokens=tokens,
    )


def test_latency_profiler_defaults():
    profiler = LatencyProfiler()
    assert profiler.warmup_steps == 0
    assert profiler.device == "cpu"


def test_latency_event_defaults():
    event = LatencyEvent(
        event_type=LatencyEventType.STEP,
        latency_ms=10.0,
        tokens=5,
    )
    assert event.latency_ms == 10.0
    assert event.tokens == 5


def test_latency_event_tokens_per_second():
    event = LatencyEvent(
        event_type=LatencyEventType.STEP,
        latency_ms=100.0,
        tokens=50,
    )
    tps = event.tokens_per_second
    assert abs(tps - 500.0) < 1.0


def test_latency_event_ms_per_token():
    event = LatencyEvent(
        event_type=LatencyEventType.STEP,
        latency_ms=100.0,
        tokens=5,
    )
    assert abs(event.ms_per_token - 20.0) < 1.0


def test_profiling_context_defaults():
    ctx = ProfilingContext(name="test_event")
    assert ctx.name == "test_event"
    assert ctx.end_time is None


def test_profiling_context_elapsed_ms():
    ctx = ProfilingContext(name="test")
    ctx.end_time = ctx.start_time + 0.05
    elapsed = ctx.elapsed_ms
    assert abs(elapsed - 50.0) < 1.0


def test_profiling_context_elapsed_seconds():
    ctx = ProfilingContext(name="test")
    ctx.end_time = ctx.start_time + 0.05
    elapsed = ctx.elapsed_seconds
    assert abs(elapsed - 0.05) < 0.01


def test_latency_event_zero_tokens():
    event = LatencyEvent(
        event_type=LatencyEventType.STEP,
        latency_ms=100.0,
        tokens=0,
    )
    assert event.tokens_per_second == 0.0
    assert event.ms_per_token == 0.0


def test_latency_profiler_record_latency():
    profiler = LatencyProfiler()
    event = profiler.record_latency(
        LatencyEventType.STEP, latency_ms=10.0, tokens=5
    )
    assert len(profiler.events) == 1


def test_latency_profiler_step_latency():
    profiler = LatencyProfiler()
    event = profiler.step_latency(latency_ms=10.0, tokens=5)
    assert event.event_type == LatencyEventType.STEP


def test_latency_profiler_get_events():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=10.0, tokens=5)
    events = profiler.get_events()
    assert len(events) == 1


def test_latency_profiler_get_events_by_type():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=10.0, tokens=5)
    profiler.record_latency(LatencyEventType.PREFILL, latency_ms=20.0, tokens=0)
    step_events = profiler.get_events_by_type(LatencyEventType.STEP)
    assert len(step_events) == 1
    prefill_events = profiler.get_events_by_type(LatencyEventType.PREFILL)
    assert len(prefill_events) == 1


def test_latency_profiler_summary_empty():
    profiler = LatencyProfiler()
    summary = profiler.summary()
    assert summary["total_events"] == 0
    assert summary["ttft_ms"] == 0.0


def test_latency_profiler_summary_with_events():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=10.0, tokens=5)
    profiler.record_latency(LatencyEventType.STEP, latency_ms=20.0, tokens=5)
    profiler.record_latency(LatencyEventType.PREFILL, latency_ms=5.0, tokens=10)
    summary = profiler.summary()
    assert summary["total_events"] == 3
    assert summary["total_tokens"] == 20
    assert abs(summary["avg_latency_ms"] - 11.67) < 1.0


def test_latency_profiler_summary_min_max():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=5.0, tokens=1)
    profiler.record_latency(LatencyEventType.STEP, latency_ms=50.0, tokens=1)
    summary = profiler.summary()
    assert abs(summary["min_latency_ms"] - 5.0) < 1e-6
    assert abs(summary["max_latency_ms"] - 50.0) < 1e-6


def test_latency_profiler_summary_ttft():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=10.0, tokens=5)
    profiler.record_latency(LatencyEventType.PREFILL, latency_ms=100.0, tokens=0)
    summary = profiler.summary()
    assert abs(summary["ttft_ms"] - 100.0) < 1e-6


def test_latency_profiler_reset():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=10.0, tokens=5)
    assert len(profiler.events) == 1
    profiler.reset()
    assert len(profiler.events) == 0


def test_latency_profiler_get_tokens_per_second():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=100.0, tokens=50)
    tps = profiler.get_tokens_per_second()
    assert abs(tps - 500.0) < 1.0


def test_latency_profiler_get_avg_latency():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=10.0, tokens=5)
    profiler.record_latency(LatencyEventType.STEP, latency_ms=20.0, tokens=5)
    avg = profiler.get_avg_latency()
    assert abs(avg - 15.0) < 1e-6


def test_latency_profiler_get_min_latency():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=10.0, tokens=5)
    profiler.record_latency(LatencyEventType.STEP, latency_ms=30.0, tokens=5)
    min_lat = profiler.get_min_latency()
    assert abs(min_lat - 10.0) < 1e-6


def test_latency_profiler_get_max_latency():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=10.0, tokens=5)
    profiler.record_latency(LatencyEventType.STEP, latency_ms=30.0, tokens=5)
    max_lat = profiler.get_max_latency()
    assert abs(max_lat - 30.0) < 1e-6


def test_latency_profiler_start_stop_event():
    profiler = LatencyProfiler()
    ctx = profiler.start_event(
        "test_event",
        event_type=LatencyEventType.STEP,
        metadata={"name": "test_event"},
    )
    time.sleep(0.01)
    event = profiler.stop_event(ctx, tokens=5)
    assert event.latency_ms > 0
    assert event.tokens == 5


def test_latency_profiler_empty_get_tokens_per_second():
    profiler = LatencyProfiler()
    tps = profiler.get_tokens_per_second()
    assert tps == 0.0


def test_latency_profiler_get_events_empty():
    profiler = LatencyProfiler()
    assert len(profiler.get_events()) == 0


def test_latency_profiler_summary_p50():
    profiler = LatencyProfiler()
    for i in range(10):
        profiler.record_latency(LatencyEventType.STEP, latency_ms=float(i + 1), tokens=1)
    summary = profiler.summary()
    assert summary["p50_latency_ms"] > 0


def test_latency_profiler_get_events_by_name():
    profiler = LatencyProfiler()
    profiler.record_latency(
        LatencyEventType.STEP, latency_ms=10.0, tokens=5,
        metadata={"name": "my_test_event"},
    )
    events = profiler.get_events_by_name("my_test")
    assert len(events) == 1


def test_latency_event_metadata():
    event = LatencyEvent(
        event_type=LatencyEventType.STEP,
        latency_ms=10.0,
        metadata={"custom": "value"},
    )
    assert event.metadata["custom"] == "value"


def test_latency_profiler_summary_avg_tps():
    profiler = LatencyProfiler()
    profiler.record_latency(LatencyEventType.STEP, latency_ms=100.0, tokens=50)
    profiler.record_latency(LatencyEventType.STEP, latency_ms=100.0, tokens=50)
    summary = profiler.summary()
    assert summary["total_tokens"] == 100
    assert summary["total_tokens_per_second"] > 0
