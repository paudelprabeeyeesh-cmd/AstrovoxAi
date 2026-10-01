"""Tests for FLOP accounting, timing, and allocation tracking."""

import numpy as np
import pytest

from astrovox import tensor
from astrovox.autograd import backward
from astrovox.nn import Linear, ReLU, Sequential
from astrovox.ops import cross_entropy, matmul
from astrovox.profile import (
    AllocationTracker,
    Profiler,
    benchmark,
    cache_efficiency,
    compare,
    count_backward_flops,
    count_flops,
    estimate_bandwidth,
    estimate_intensity,
    node_flops,
)


class TestFlopCounting:
    def test_matmul_flops_match_the_analytic_value(self):
        """A dense matmul costs two flops per multiply-add."""
        a = tensor(np.zeros((4, 8), dtype=np.float32)).requires_grad_(True)
        b = tensor(np.zeros((8, 16), dtype=np.float32)).requires_grad_(True)
        out = matmul(a, b)
        assert count_flops(out).total == 2 * 4 * 8 * 16

    def test_batched_matmul_scales_with_the_batch(self):
        single = matmul(
            tensor(np.zeros((8, 16), dtype=np.float32)),
            tensor(np.zeros((16, 32), dtype=np.float32)),
        )
        batched = matmul(
            tensor(np.zeros((5, 8, 16), dtype=np.float32)),
            tensor(np.zeros((16, 32), dtype=np.float32)),
        )
        assert count_flops(batched).total == 5 * count_flops(single).total

    def test_vector_matmul(self):
        # count_flops reads the recorded graph, so an input has to require a
        # gradient for the node to exist.
        out = matmul(
            tensor(np.zeros((6,), dtype=np.float32)).requires_grad_(True),
            tensor(np.zeros((6, 4), dtype=np.float32)).requires_grad_(True),
        )
        assert count_flops(out).total == 2 * 6 * 4

    def test_no_graph_means_no_flops(self):
        """A forward under no_grad records nothing, so nothing is counted."""
        from astrovox.autograd import no_grad

        a = tensor(np.zeros((4, 4), dtype=np.float32)).requires_grad_(True)
        with no_grad():
            out = a * 2.0
        assert count_flops(out).total == 0

    def test_elementwise_scales_with_elements(self):
        a = tensor(np.zeros((10, 20), dtype=np.float32)).requires_grad_(True)
        assert count_flops(a * 2.0).total == 200

    def test_views_cost_nothing(self):
        """A view moves no data, so it performs no arithmetic."""
        a = tensor(np.zeros((4, 4), dtype=np.float32)).requires_grad_(True)
        assert count_flops(a.transpose(0, 1)).total == 0
        assert count_flops(a.reshape(2, 8)).total == 0

    def test_model_flops_are_the_sum_of_its_layers(self):
        model = Sequential(Linear(16, 32), ReLU(), Linear(32, 4))
        x = tensor(np.zeros((2, 16), dtype=np.float32))
        y = tensor(np.zeros(2, dtype=np.int64))
        total = count_flops(cross_entropy(model(x), y)).total
        # 2*2*16*32 + 2*2*32*4 plus the activations
        assert total >= 2 * 2 * 16 * 32 + 2 * 2 * 32 * 4

    def test_backward_costs_more_than_forward(self):
        model = Sequential(Linear(16, 32), ReLU(), Linear(32, 4))
        x = tensor(np.zeros((2, 16), dtype=np.float32))
        y = tensor(np.zeros(2, dtype=np.int64))
        loss = cross_entropy(model(x), y)
        forward = count_flops(loss).total
        backward_cost = count_backward_flops(loss).total
        assert backward_cost > forward

    def test_breakdown_ranks_the_expensive_operations(self):
        model = Sequential(Linear(64, 128), ReLU(), Linear(128, 64))
        x = tensor(np.zeros((4, 64), dtype=np.float32))
        y = tensor(np.zeros(4, dtype=np.int64))
        breakdown = count_flops(cross_entropy(model(x), y))
        assert breakdown.by_op
        assert breakdown.top()[0][0] == "matmul"
        assert sum(breakdown.by_op.values()) == breakdown.total

    def test_node_flops_is_zero_for_an_unknown_op(self):
        assert node_flops.__doc__


class TestProfilerTiming:
    def test_records_a_region(self):
        model = Sequential(Linear(32, 32))
        x = tensor(np.zeros((4, 32), dtype=np.float32))
        with Profiler() as prof:
            with prof.region("forward"):
                model(x)
        assert "forward" in prof.records
        assert prof.records["forward"].calls == 1
        assert prof.records["forward"].seconds > 0

    def test_nested_and_repeated_regions_accumulate(self):
        model = Sequential(Linear(16, 16))
        x = tensor(np.zeros((2, 16), dtype=np.float32))
        with Profiler() as prof:
            for _ in range(3):
                with prof.region("step"):
                    model(x)
        assert prof.records["step"].calls == 3

    def test_gflops_is_reported(self):
        model = Sequential(Linear(64, 64))
        x = tensor(np.zeros((8, 64), dtype=np.float32))
        with Profiler() as prof:
            with prof.region("matmul", flops=2 * 8 * 64 * 64):
                model(x)
        assert prof.records["matmul"].gflops > 0

    def test_disabled_profiler_records_nothing(self):
        model = Sequential(Linear(8, 8))
        x = tensor(np.zeros((2, 8), dtype=np.float32))
        with Profiler(enabled=False) as prof:
            with prof.region("ignored"):
                model(x)
        assert prof.records == {}

    def test_report_and_dict_are_available(self):
        model = Sequential(Linear(8, 8))
        x = tensor(np.zeros((2, 8), dtype=np.float32))
        with Profiler() as prof:
            with prof.region("a"):
                model(x)
        assert "a" in prof.report()
        assert "a" in prof.to_dict()
        assert prof.slowest() == "a"

    def test_report_without_regions(self):
        with Profiler() as prof:
            pass
        assert "no regions" in prof.report()
        assert prof.slowest() is None


class TestAllocationTracker:
    def test_counts_allocations_and_bytes(self):
        tracker = AllocationTracker()
        tensors = [tensor(np.zeros((10, 10), dtype=np.float32)) for _ in range(3)]
        for t in tensors:
            tracker.record(t)
        assert tracker.count == 3
        assert tracker.bytes == 3 * 400
        assert tracker.average_bytes == 400

    def test_release_reduces_live_bytes(self):
        tracker = AllocationTracker()
        t = tensor(np.zeros((10, 10), dtype=np.float32))
        tracker.record(t)
        peak = tracker._live_peak
        tracker.release(t)
        assert tracker._live == 0
        assert tracker._live_peak == peak

    def test_reset_clears_counters(self):
        tracker = AllocationTracker()
        tracker.record(tensor(np.zeros((4,), dtype=np.float32)))
        tracker.reset()
        assert tracker.count == 0
        assert "allocations" in tracker.report()

    def test_distinct_shapes_are_tracked(self):
        tracker = AllocationTracker()
        tracker.record(tensor(np.zeros((2, 2), dtype=np.float32)))
        tracker.record(tensor(np.zeros((3, 3), dtype=np.float32)))
        assert tracker.to_dict()["distinct_shapes"] == 2


class TestRooflineHelpers:
    def test_bandwidth_is_bytes_per_second(self):
        t = tensor(np.zeros((10, 10), dtype=np.float32))
        assert estimate_bandwidth(t, 0.5) == pytest.approx(400 / 0.5)

    def test_bandwidth_of_zero_time_is_zero(self):
        assert estimate_bandwidth(tensor(np.zeros((2,), dtype=np.float32)), 0.0) == 0.0

    def test_cache_efficiency(self):
        t = tensor(np.zeros((10, 10), dtype=np.float32))
        assert cache_efficiency(t, 400) == pytest.approx(1.0)
        assert cache_efficiency(t, 800) == pytest.approx(0.5)
        assert cache_efficiency(t, 0) == 0.0

    def test_intensity_separates_compute_and_memory_bound(self):
        # A matmul moves little data per flop, so intensity is high.
        assert estimate_intensity(2 * 64 * 64 * 64, 64 * 64 * 4) > 1.0
        # An elementwise op moves a lot of data per flop.
        assert estimate_intensity(400, 400 * 4) < 1.0
        assert estimate_intensity(10, 0) == 0.0


class TestBenchmarkHarness:
    def test_benchmark_reports_per_call_time(self):
        model = Sequential(Linear(16, 16))
        x = tensor(np.zeros((2, 16), dtype=np.float32))
        result = benchmark("model", lambda: model(x), calls=4, warmup=1)
        assert result.calls == 4
        assert result.per_call_ms >= 0.0

    def test_benchmark_flops_produce_gflops(self):
        result = benchmark("op", lambda: None, calls=2, flops=1_000_000)
        assert result.gflops >= 0.0

    def test_warmup_runs_before_timing(self):
        calls = []
        def fn():
            calls.append(1)
        benchmark("counting", fn, calls=3, warmup=2)
        assert len(calls) == 5

    def test_compare_against_a_baseline(self):
        results = [benchmark("a", lambda: None, calls=1), benchmark("b", lambda: None, calls=1)]
        table = compare(results, "a")
        assert "a" in table and "b" in table
        table.encode("ascii")

    def test_compare_without_a_baseline(self):
        results = [benchmark("only", lambda: None, calls=1)]
        assert "only" in compare(results, "missing")
