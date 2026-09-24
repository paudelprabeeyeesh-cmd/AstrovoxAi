import hashlib

from backup_recovery.snapshot_manager import Snapshot, SnapshotManager


def test_create_and_get_snapshot():
    manager = SnapshotManager()
    data = b"hello world"
    snapshot = manager.create_snapshot(data, label="test")
    assert snapshot.backup_id is not None
    assert snapshot.timestamp > 0
    assert snapshot.size_bytes == len(data)
    assert snapshot.label == "test"

    retrieved = manager.get_snapshot(snapshot.backup_id)
    assert retrieved is snapshot


def test_list_snapshots():
    manager = SnapshotManager()
    manager.create_snapshot(b"a", label="a")
    manager.create_snapshot(b"bb", label="b")
    manager.create_snapshot(b"ccc", label="c")
    snapshots = manager.list_snapshots()
    assert len(snapshots) == 3
    assert [s.label for s in snapshots] == ["a", "b", "c"]


def test_point_in_time():
    manager = SnapshotManager()
    s1 = manager.create_snapshot(b"a", label="s1")
    import time
    time.sleep(0.01)
    s2 = manager.create_snapshot(b"bb", label="s2")

    result = manager.point_in_time(s1.timestamp)
    assert result.backup_id == s1.backup_id

    result = manager.point_in_time(s2.timestamp)
    assert result.backup_id == s2.backup_id

    result = manager.point_in_time(s1.timestamp + 0.005)
    assert result.backup_id == s1.backup_id


def test_snapshot_checksum():
    manager = SnapshotManager()
    data = b"hello world"
    snapshot = manager.create_snapshot(data)
    expected = hashlib.sha256(data).hexdigest()
    assert snapshot.checksum == expected


def test_snapshot_lock():
    manager = SnapshotManager()
    manager._lock = True
    try:
        manager.create_snapshot(b"a")
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "already in progress" in str(e)
