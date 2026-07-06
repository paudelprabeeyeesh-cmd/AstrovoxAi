import pytest

from app.usage import DailyUsageTracker, UsageQuotaExceeded


@pytest.mark.asyncio
async def test_daily_usage_tracker_blocks_excess_requests():
    tracker = DailyUsageTracker(limit=2)

    await tracker.record_success("user-1")
    await tracker.record_success("user-1")

    with pytest.raises(UsageQuotaExceeded):
        await tracker.record_success("user-1")

    assert await tracker.get_count("user-1") == 2
