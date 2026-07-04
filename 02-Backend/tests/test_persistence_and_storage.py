import pytest

from app.storage import StorageService
from app.usage import DailyUsageTracker, UsageQuotaExceeded


@pytest.mark.asyncio
async def test_persistent_usage_tracker_uses_local_store(tmp_path):
    tracker = DailyUsageTracker(limit=1, storage_path=str(tmp_path / "usage.sqlite3"))

    await tracker.record_success("user-1")

    with pytest.raises(UsageQuotaExceeded):
        await tracker.record_success("user-1")

    assert await tracker.get_count("user-1") == 1


def test_storage_service_uploads_and_enforces_owner_paths(tmp_path):
    service = StorageService(base_dir=str(tmp_path))

    result = service.upload_file(
        "user-1",
        "avatars",
        "user/user-1/profile.png",
        b"fake-image",
        content_type="image/png",
    )

    assert result["path"].endswith("profile.png")
    assert result["bucket"] == "avatars"

    signed_url = service.get_signed_url("user-1", "avatars", "user/user-1/profile.png")
    assert "profile.png" in signed_url["url"]

    with pytest.raises(ValueError):
        service.upload_file(
            "user-1",
            "avatars",
            "user/user-2/profile.png",
            b"fake-image",
            content_type="image/png",
        )
