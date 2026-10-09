import numpy as np
import pytest

from observability.latency_metrics import LatencyMetrics


def test_empty_ttft_p50_none():
    lm = LatencyMetrics()
    assert lm.ttft_p50() is None


def test_empty_ttft_p99_none():
    lm = LatencyMetrics()
    assert lm.ttft_p99() is None


def test_empty_inter_token_p50_none():
    lm = LatencyMetrics()
    assert lm.inter_token_p50() is None


def test_empty_total_p50_none():
    lm = LatencyMetrics()
    assert lm.total_p50() is None


def test_record_and_ttft_percentiles():
    lm = LatencyMetrics()
    for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
        lm.record_ttft(v)
    p50 = lm.ttft_p50()
    p99 = lm.ttft_p99()
    assert p50 is not None
    assert p99 is not None
    assert 10.0 <= p50 <= 50.0
    assert 10.0 <= p99 <= 50.0


def test_record_and_inter_token_percentiles():
    lm = LatencyMetrics()
    for v in [1.0, 2.0, 3.0]:
        lm.record_inter_token(v)
    p50 = lm.inter_token_p50()
    assert p50 is not None
    assert p50 == pytest.approx(2.0)


def test_record_and_total_percentiles():
    lm = LatencyMetrics()
    for v in [100.0, 200.0, 300.0]:
        lm.record_total(v)
    p99 = lm.total_p99()
    assert p99 is not None
    assert 100.0 <= p99 <= 300.0


def test_summary_keys():
    lm = LatencyMetrics()
    lm.record_ttft(10.0)
    lm.record_inter_token(2.0)
    lm.record_total(100.0)
    s = lm.summary()
    assert "ttft_p50" in s
    assert "ttft_p99" in s
    assert "inter_token_p50" in s
    assert "inter_token_p99" in s
    assert "total_p50" in s
    assert "total_p99" in s


def test_summary_none_for_empty():
    lm = LatencyMetrics()
    s = lm.summary()
    assert s["ttft_p50"] is None


def test_thread_safety():
    lm = LatencyMetrics()
    import threading

    def worker():
        for v in [1.0, 2.0, 3.0]:
            lm.record_ttft(v)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(lm._ttft) == 4 * 3


def test_percentile_computation_via_numpy():
    lm = LatencyMetrics()
    values = [10.0, 20.0, 30.0]
    for v in values:
        lm.record_ttft(v)
    p50 = lm.ttft_p50()
    assert p50 == pytest.approx(np.percentile(values, 50))
