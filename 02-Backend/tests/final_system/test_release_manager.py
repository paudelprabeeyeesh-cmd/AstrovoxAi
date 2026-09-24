import pytest
from final_system.release_manager import Release, ReleaseManager, ReleaseStatus


def test_create_release():
    manager = ReleaseManager()
    release = manager.create_release("1.0.0", artifacts=["a.zip"])
    assert release.version == "1.0.0"
    assert release.artifacts == ["a.zip"]
    assert release.status == ReleaseStatus.DRAFT


def test_promote_release():
    manager = ReleaseManager()
    manager.create_release("1.0.0")
    release = manager.promote("1.0.0", ReleaseStatus.RELEASED)
    assert release.status == ReleaseStatus.RELEASED


def test_get_release_missing():
    manager = ReleaseManager()
    with pytest.raises(KeyError):
        manager.get_release("missing")


def test_list_releases():
    manager = ReleaseManager()
    manager.create_release("1.0.0")
    manager.create_release("2.0.0")
    assert manager.list_releases() == ["1.0.0", "2.0.0"]
