import time
import pytest
from advanced_backend.backup_recovery import BackupStore


def test_snapshot_and_list():
    store = BackupStore()
    manifest = store.snapshot(b"hello world", label="daily")
    assert manifest.size_bytes == 11
    backups = store.list_backups()
    assert len(backups) == 1
    assert backups[0]["label"] == "daily"


def test_restore():
    store = BackupStore()
    m = store.snapshot(b"data", label="x")
    data = store.restore(m.backup_id)
    assert data is not None


def test_point_in_time():
    store = BackupStore()
    store.snapshot(b"old", label="old")
    time.sleep(0.01)
    mid = store.snapshot(b"new", label="new")
    target = store.point_in_time(store._manifests[1].timestamp - 0.001)
    assert target is not None
    assert target.backup_id == store._manifests[0].backup_id
