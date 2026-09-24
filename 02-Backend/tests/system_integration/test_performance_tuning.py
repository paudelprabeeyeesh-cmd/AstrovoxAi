import pytest
from system_integration.performance_tuning import (
    Bottleneck,
    ConnectionPool,
    ProfileEntry,
    Profiler,
    BatchProcessor,
    PerformanceOptimizer,
)


def test_profiler_record():
    p = Profiler()
    p.record(ProfileEntry(component="db", duration_ms=10.0))
    assert len(p._entries) == 1


def test_profiler_report():
    p = Profiler()
    p.record(ProfileEntry(component="db", duration_ms=10.0))
    p.record(ProfileEntry(component="db", duration_ms=30.0))
    p.record(ProfileEntry(component="cache", duration_ms=5.0))
    bns = p.report()
    assert bns[0].component == "db"
    assert abs(bns[0].avg_duration_ms - 20.0) < 0.01


def test_profiler_disable():
    p = Profiler()
    p.disable()
    p.record(ProfileEntry(component="x", duration_ms=1.0))
    assert len(p._entries) == 0


def test_batch_processor():
    bp = BatchProcessor(batch_size=2)
    bp._process = lambda item: item
    bp.submit("a")
    bp.submit("b")
    assert len(bp._queue) == 0


def test_connection_pool():
    pool = ConnectionPool(max_size=2)
    assert pool.size() == 0


def test_performance_optimizer_apply_all():
    p = Profiler()
    opt = PerformanceOptimizer(p)
    flag = []
    def strategy(): flag.append(1)
    opt.register_strategy("x", strategy)
    p.record(ProfileEntry(component="x", duration_ms=500.0))
    optimized = opt.optimize_all(thresholds={"x": 10.0})
    assert flag == [1]
    assert optimized == ["x"]


def test_optimizer_no_apply_below_threshold():
    p = Profiler()
    opt = PerformanceOptimizer(p)
    flag = []
    def strategy(): flag.append(1)
    opt.register_strategy("x", strategy)
    p.record(ProfileEntry(component="x", duration_ms=1.0))
    optimized = opt.optimize_all(thresholds={"x": 10.0})
    assert flag == []
    assert optimized == []
