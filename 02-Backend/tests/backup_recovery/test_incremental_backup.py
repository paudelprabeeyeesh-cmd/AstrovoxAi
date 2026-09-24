from backup_recovery.incremental_backup import (
    IncrementalBackup,
    IncrementalBackupManager,
)


def test_start_and_get_backup():
    manager = IncrementalBackupManager()
    backup_id = manager.start_backup(label="test")
    assert backup_id is not None

    backup = manager.get_backup(backup_id)
    assert backup is not None
    assert backup.label == "test"
    assert backup.end_time is None


def test_record_changes_and_complete():
    manager = IncrementalBackupManager()
    backup_id = manager.start_backup(label="inc")
    manager.record_changes(backup_id, [b"change1", b"change2"])
    backup = manager.get_backup(backup_id)
    assert len(backup.changes) == 2

    manager.complete_backup(backup_id)
    assert backup.end_time is not None
    assert backup.metadata["total_size"] == sum(len(c) for c in backup.changes)
    assert backup.metadata["change_count"] == len(backup.changes)


def test_list_backups():
    manager = IncrementalBackupManager()
    manager.start_backup(label="a")
    manager.start_backup(label="b")
    backups = manager.list_backups()
    assert len(backups) == 2
    assert [b.label for b in backups] == ["a", "b"]


def test_complete_backup_twice():
    manager = IncrementalBackupManager()
    backup_id = manager.start_backup(label="a")
    manager.complete_backup(backup_id)
    try:
        manager.complete_backup(backup_id)
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "already completed" in str(e)


def test_record_changes_after_complete():
    manager = IncrementalBackupManager()
    backup_id = manager.start_backup(label="a")
    manager.complete_backup(backup_id)
    try:
        manager.record_changes(backup_id, [b"a"])
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "already completed" in str(e)


def test_backup_not_found():
    manager = IncrementalBackupManager()
    try:
        manager.get_backup("nonexistent")
        assert False, "Should have raised KeyError"
    except KeyError:
        pass

    try:
        manager.record_changes("nonexistent", [b"a"])
        assert False, "Should have raised KeyError"
    except KeyError:
        pass
