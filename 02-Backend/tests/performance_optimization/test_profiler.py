import time

from performance_optimization.profiler import Profiler, ProfileRecord


def test_profiler_records_multiple_entries():
    profiler = Profiler()
    profiler.record("foo", 0.1)
    profiler.record("foo", 0.2)
    profiler.record("bar", 0.05)
    report = profiler.report()
    names = {r.name for r in report}
    assert names == {"foo", "bar"}
    foo = next(r for r in report if r.name == "foo")
    assert foo.iterations == 2
    assert abs(foo.total_seconds - 0.3) < 1e-9
    assert abs(foo.per_iteration_ms - 150.0) < 1e-6


def test_profiler_timer_context_manager():
    profiler = Profiler()
    with profiler.timer("sleepy"):
        time.sleep(0.01)
    report = profiler.report()
    assert len(report) == 1
    assert report[0].name == "sleepy"
    assert report[0].per_iteration_ms >= 10.0


def test_profiler_wrap_function():
    profiler = Profiler()

    @profiler.wrap_function("add")
    def add(a, b):
        return a + b

    assert add(1, 2) == 3
    report = profiler.report()
    assert report[0].name == "add"
    assert report[0].iterations == 1


def test_profiler_reset_clears_records():
    profiler = Profiler()
    profiler.record("x", 0.1)
    profiler.reset()
    assert profiler.report() == []


def test_profiler_report_as_json():
    profiler = Profiler()
    profiler.record("x", 0.1)
    output = profiler.report(as_json=True)
    assert "x" in output
    assert "total_seconds" in output
