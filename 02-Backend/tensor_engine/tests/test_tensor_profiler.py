import time
import tracemalloc
import numpy as np
import pytest
from tensor_engine.tensor_profiler import TensorProfiler


class TestTensorProfilerInit:
    def test_init(self):
        p = TensorProfiler()
        assert p._records == []
        assert p.cache_info()["calls"] == 0

    def test_init_starts_tracemalloc(self):
        assert tracemalloc.is_tracing()


class TestTensorProfilerProfile:
    def test_profile_basic(self):
        p = TensorProfiler()
        result = p.profile("square", lambda x: x * x, 3)
        assert result == 9

    def test_profile_records_name(self):
        p = TensorProfiler()
        p.profile("square", lambda x: x * x, 3)
        assert p.cache_info()["calls"] == 1

    def test_profile_returns_result(self):
        p = TensorProfiler()
        arr = np.random.randn(2, 3)
        result = p.profile("identity", lambda x: x, arr)
        np.testing.assert_array_equal(result, arr)

    def test_profile_result_shape_recorded(self):
        p = TensorProfiler()
        arr = np.random.randn(2, 3)
        p.profile("identity", lambda x: x, arr)
        record = p.cache_info()["records"][0]
        assert record["result_shape"] == (2, 3)

    def test_profile_no_result(self):
        p = TensorProfiler()
        result = p.profile("none", lambda: None)
        assert result is None

    def test_profile_time_record(self):
        p = TensorProfiler()
        def slow(x):
            time.sleep(0.01)
            return x
        p.profile("slow", slow, 1)
        record = p.cache_info()["records"][0]
        assert record["time"] >= 0.01

    def test_profile_multiple_calls(self):
        p = TensorProfiler()
        for i in range(5):
            p.profile(f"fn{i}", lambda x: x, i)
        assert p.cache_info()["calls"] == 5

    def test_profile_with_args(self):
        p = TensorProfiler()
        def add(a, b):
            return a + b
        result = p.profile("add", add, 2, 3)
        assert result == 5

    def test_profile_with_kwargs(self):
        p = TensorProfiler()
        def multiply(a, b=2):
            return a * b
        result = p.profile("multiply", multiply, 3, b=4)
        assert result == 12

    def test_profile_numpy_array(self):
        p = TensorProfiler()
        arr = np.random.randn(10, 10)
        result = p.profile("matmul", np.dot, arr, arr)
        assert result.shape == (10, 10)

    def test_profile_result_shape_none_for_none(self):
        p = TensorProfiler()
        p.profile("none", lambda: None)
        record = p.cache_info()["records"][0]
        assert record["result_shape"] is None

    def test_profile_memory_recorded_positive(self):
        p = TensorProfiler()
        def make_array():
            return np.zeros(1000)
        p.profile("make", make_array)
        record = p.cache_info()["records"][0]
        assert record["mem_delta"] >= 0


class TestTensorProfilerReport:
    def test_report_basic(self):
        p = TensorProfiler()
        p.profile("square", lambda x: x * x, 3)
        p.profile("double", lambda x: x * 2, 5)
        report = p.report()
        assert report["calls"] == 2
        assert len(report["records"]) == 2

    def test_report_total_time(self):
        p = TensorProfiler()
        def slow(x):
            time.sleep(0.02)
            return x
        p.profile("slow", slow, 1)
        report = p.report()
        assert report["total_time"] >= 0.02

    def test_report_total_mem(self):
        p = TensorProfiler()
        p.profile("create", lambda: np.zeros(1000),)
        report = p.report()
        assert report["total_mem_delta"] >= 0

    def test_report_empty(self):
        p = TensorProfiler()
        report = p.report()
        assert report["calls"] == 0
        assert report["total_time"] == 0
        assert report["total_mem_delta"] == 0

    def test_report_sums(self):
        p = TensorProfiler()
        p.profile("a", lambda: 1)
        p.profile("b", lambda: 2)
        report = p.report()
        assert report["calls"] == 2
        assert len(report["records"]) == 2


class TestTensorProfilerReset:
    def test_reset(self):
        p = TensorProfiler()
        p.profile("square", lambda x: x * x, 3)
        assert p.cache_info()["calls"] == 1
        p.reset()
        assert p.cache_info()["calls"] == 0
        assert p._records == []

    def test_reset_then_profile(self):
        p = TensorProfiler()
        p.profile("fn1", lambda: 1)
        p.reset()
        p.profile("fn2", lambda: 2)
        assert p.cache_info()["calls"] == 1
        assert p.cache_info()["records"][0]["name"] == "fn2"


class TestTensorProfilerStop:
    def test_stop(self):
        p = TensorProfiler()
        p.stop()
        assert p.cache_info()["calls"] == 0

    def test_stop_then_profile(self):
        p = TensorProfiler()
        p.stop()
        with pytest.raises(RuntimeError):
            p.profile("fn", lambda: 42)
