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


def test_schedule_backup():
    mgr = BackupManager()
    calls = []

    def callback():
        calls.append(1)

    mgr.schedule_backup(0.05, callback)
    time.sleep(0.12)
    assert len(calls) >= 2
    mgr.stop_schedule()
