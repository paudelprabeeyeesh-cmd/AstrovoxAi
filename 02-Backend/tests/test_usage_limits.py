import pytest
from app.usage import DailyUsageTracker, UsageQuotaExceeded


@pytest.mark.asyncio
async def test_daily_usage_tracker_blocks_excess_requests(tmp_path):
    tracker = DailyUsageTracker(limit=2, storage_path=str(tmp_path / "usage.db"))

    await tracker.record_success("user-1")
    await tracker.record_success("user-1")

    with pytest.raises(UsageQuotaExceeded):
        await tracker.record_success("user-1")

    assert await tracker.get_count("user-1") == 2


@pytest.mark.asyncio
async def test_daily_usage_tracker_counts_independent_users(tmp_path):
    tracker = DailyUsageTracker(limit=2, storage_path=str(tmp_path / "usage.db"))

    await tracker.record_success("user-a")
    await tracker.record_success("user-b")

    assert await tracker.get_count("user-a") == 1
    assert await tracker.get_count("user-b") == 1


@pytest.mark.asyncio
async def test_daily_usage_tracker_get_count_starts_at_zero(tmp_path):
    tracker = DailyUsageTracker(limit=5, storage_path=str(tmp_path / "usage.db"))
    assert await tracker.get_count("new-user") == 0
