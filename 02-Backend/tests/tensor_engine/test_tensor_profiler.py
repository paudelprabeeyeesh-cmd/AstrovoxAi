import numpy as np
import pytest

from tensor_engine.tensor_profiler import TensorProfiler


def test_tensor_profiler_profile():
    profiler = TensorProfiler()

    def func(x):
        return x * 2

    result = profiler.profile("double", func, np.array([1.0, 2.0]))
    np.testing.assert_array_equal(result, np.array([2.0, 4.0]))


def test_tensor_profiler_cache_info():
    profiler = TensorProfiler()
    profiler.profile("a", lambda x: x, 1)
    profiler.profile("b", lambda x: x, 2)
    info = profiler.cache_info()
    assert info["calls"] == 2
    assert len(info["records"]) == 2


def test_tensor_profiler_report():
    profiler = TensorProfiler()
    profiler.profile("a", lambda: 1)
    profiler.profile("b", lambda: 2)
    report = profiler.report()
    assert report["calls"] == 2
    assert "total_time" in report
    assert "total_mem_delta" in report


def test_tensor_profiler_reset():
    profiler = TensorProfiler()
    profiler.profile("a", lambda: 1)
    profiler.reset()
    assert profiler.cache_info()["calls"] == 0


def test_tensor_profiler_result_shape():
    profiler = TensorProfiler()
    result = profiler.profile("matrix", np.ones, (2, 3))
    assert result.shape == (2, 3)
    record = profiler.cache_info()["records"][-1]
    assert record["result_shape"] == (2, 3)


def test_tensor_profiler_none_result_shape():
    profiler = TensorProfiler()
    result = profiler.profile("none_func", lambda: None)
    assert result is None
    record = profiler.cache_info()["records"][-1]
    assert record["result_shape"] is None
