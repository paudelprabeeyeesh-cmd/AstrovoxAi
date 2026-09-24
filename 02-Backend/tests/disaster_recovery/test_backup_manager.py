import hashlib
import time

from disaster_recovery.backup_manager import BackupManager, BackupRecord


def test_create_backup():
    mgr = BackupManager()
    record = mgr.create_backup(b"hello world", label="daily")
    assert record.size_bytes == 11
    assert record.label == "daily"
    assert record.checksum


def test_list_backups():
    mgr = BackupManager()
    mgr.create_backup(b"one", label="a")
    mgr.create_backup(b"two", label="b")
    backups = mgr.list_backups()
    assert len(backups) == 2
    assert backups[0]["label"] == "a"
    assert backups[1]["label"] == "b"


def test_get_backup():
    mgr = BackupManager()
    record = mgr.create_backup(b"data")
    fetched = mgr.get_backup(record.backup_id)
    assert fetched is not None
    assert fetched.backup_id == record.backup_id


def test_delete_backup():
    mgr = BackupManager()
    record = mgr.create_backup(b"data")
    assert mgr.delete_backup(record.backup_id) is True
    assert mgr.get_backup(record.backup_id) is None
    assert mgr.delete_backup(record.backup_id) is False


def test_stop_schedule_when_not_scheduled():
    mgr = BackupManager()
    mgr.stop_schedule()


def test_create_backup_with_source_and_metadata():
    mgr = BackupManager()
    record = mgr.create_backup(
        b"data",
        label="lbl",
        source="db-primary",
    )
    assert record.source == "db-primary"
    assert record.metadata == {}


def test_create_backup_empty_data():
    mgr = BackupManager()
    record = mgr.create_backup(b"", label="empty")
    assert record.size_bytes == 0
    assert record.checksum == hashlib.sha256(b"").hexdigest()


def test_list_backups_empty():
    mgr = BackupManager()
    assert mgr.list_backups() == []


def test_delete_backup_unknown():
    mgr = BackupManager()
    assert mgr.delete_backup("missing") is False


def test_schedule_backup_already_active():
    mgr = BackupManager()
    mgr.schedule_backup(0.1, lambda: None)
    try:
        mgr.schedule_backup(0.1, lambda: None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")
    finally:
        mgr.stop_schedule()
