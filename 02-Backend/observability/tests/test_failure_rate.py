import pytest

from observability.failure_rate import FailureRateTracker


def test_failure_count_zero_initially():
    ft = FailureRateTracker()
    assert ft.failure_count() == 0
    assert ft.success_count() == 0


def test_record_success():
    ft = FailureRateTracker()
    ft.record_success()
    assert ft.success_count() == 1
    assert ft.total_requests() == 1


def test_record_failure():
    ft = FailureRateTracker()
    ft.record_failure(ft.CATEGORY_TIMEOUT, "timed out")
    assert ft.failure_count() == 1
    assert ft.total_requests() == 1


def test_overall_failure_rate_none():
    ft = FailureRateTracker()
    assert ft.overall_failure_rate() is None


def test_overall_failure_rate():
    ft = FailureRateTracker()
    ft.record_success()
    ft.record_failure(ft.CATEGORY_TIMEOUT)
    rate = ft.overall_failure_rate()
    assert rate == pytest.approx(0.5)


def test_failure_rate_by_category_none():
    ft = FailureRateTracker()
    result = ft.failure_rate_by_category()
    assert all(v is None for v in result.values())


def test_failure_rate_by_category():
    ft = FailureRateTracker()
    ft.record_success()
    ft.record_success()
    ft.record_failure(ft.CATEGORY_TIMEOUT)
    result = ft.failure_rate_by_category()
    assert result[ft.CATEGORY_TIMEOUT] == pytest.approx(1 / 3)
    assert result[ft.CATEGORY_TOOL_FAILURE] == pytest.approx(0.0)


def test_count_by_category():
    ft = FailureRateTracker()
    ft.record_failure(ft.CATEGORY_TIMEOUT)
    ft.record_failure(ft.CATEGORY_TIMEOUT)
    ft.record_failure(ft.CATEGORY_MODERATION_BLOCK)
    result = ft.count_by_category()
    assert result[ft.CATEGORY_TIMEOUT] == 2
    assert result[ft.CATEGORY_MODERATION_BLOCK] == 1


def test_failure_rate_per_category_of_failures_none():
    ft = FailureRateTracker()
    result = ft.failure_rate_per_category_of_failures()
    assert all(v is None for v in result.values())


def test_failure_rate_per_category_of_failures():
    ft = FailureRateTracker()
    ft.record_failure(ft.CATEGORY_TIMEOUT)
    ft.record_failure(ft.CATEGORY_TIMEOUT)
    ft.record_failure(ft.CATEGORY_MODERATION_BLOCK)
    result = ft.failure_rate_per_category_of_failures()
    assert result[ft.CATEGORY_TIMEOUT] == pytest.approx(2 / 3)
    assert result[ft.CATEGORY_MODERATION_BLOCK] == pytest.approx(1 / 3)


def test_total_requests():
    ft = FailureRateTracker()
    ft.record_success()
    ft.record_success()
    ft.record_failure(ft.CATEGORY_TIMEOUT)
    assert ft.total_requests() == 3


def test_failure_details():
    ft = FailureRateTracker()
    ft.record_failure(ft.CATEGORY_TOOL_FAILURE, "tool crashed")
    assert ft._failures[0]["details"] == "tool crashed"
