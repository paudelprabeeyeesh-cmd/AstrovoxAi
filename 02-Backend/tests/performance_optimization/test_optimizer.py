from unittest.mock import patch

from performance_optimization.optimizer import (
    OptimizationReport,
    backoff_wait,
    batch_invoke,
    make_cache_key,
    memoize,
    optimize,
    run_optimized,
    tune_batch_size,
    tune_with_backoff,
    to_json,
)


def test_make_cache_key_format():
    key = make_cache_key("func", (1, 2), {"b": 3})
    assert key == "func:(1, 2):[('b', 3)]"


def test_memoize_caches_result():
    registry = {}
    calls = []

    @memoize(registry, "add")
    def add(a, b):
        calls.append((a, b))
        return a + b

    assert add(1, 2) == 3
    assert add(1, 2) == 3
    assert len(calls) == 1


def test_batch_invoke_respects_batch_size():
    results = batch_invoke({}, "test", lambda x: x * 2, [1, 2, 3, 4], batch_size=2, delay=0.0)
    assert results == [2, 4, 6, 8]


def test_backoff_wait_caps():
    wait = backoff_wait(10, base=0.05, cap=0.5, factor=2.0)
    assert 0.5 <= wait <= 0.51


def test_tune_batch_size_within_range():
    size = tune_batch_size({}, "test", 4, 8)
    assert 4 <= size <= 8


def test_run_optimized_reports_improvement():
    registry = {}
    registry["func_original"] = 0.2
    report = run_optimized(registry, "func", lambda x: x, [1, 2, 3])
    assert isinstance(report, OptimizationReport)
    assert report.original == 0.2
    assert report.optimized >= 0


def test_tune_with_backoff_succeeds():
    registry = {}
    exc = tune_with_backoff(registry, "ok", lambda: None)
    assert exc is None


def test_tune_with_backoff_fails():
    registry = {}

    def failing():
        raise RuntimeError("boom")

    with patch("performance_optimization.optimizer.time.sleep"):
        exc = tune_with_backoff(registry, "bad", failing)
    assert isinstance(exc, RuntimeError)


def test_optimize_returns_positive_improvement():
    registry = {}
    counters = [0.0, 0.1, 0.11, 0.111]

    def slow_func(x):
        return x

    with patch("performance_optimization.optimizer.time.perf_counter", side_effect=counters):
        report = optimize(registry, "slow", slow_func, [1, 2, 3])
    assert isinstance(report, OptimizationReport)
    assert report.original > report.optimized
    assert report.improvement_ms > 0
    assert 0 < report.improvement_share < 1


def test_to_json_serializable():
    report = OptimizationReport(original=0.1, optimized=0.05, improvement_ms=50.0, improvement_share=0.5)
    json_str = to_json(report)
    assert "0.1" in json_str
