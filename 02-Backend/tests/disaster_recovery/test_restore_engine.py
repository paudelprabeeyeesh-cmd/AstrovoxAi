import os
import tempfile

from disaster_recovery.backup_manager import BackupManager
from disaster_recovery.restore_engine import RestoreEngine


def test_restore_success():
    mgr = BackupManager()
    engine = RestoreEngine(mgr)
    record = mgr.create_backup(b"restore me", label="snap")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        dest = tmp.name
    try:
        result = engine.restore(record.backup_id, dest, b"restore me")
        assert result.success is True
        assert result.bytes_written == 9
        with open(dest, "rb") as f:
            assert f.read() == b"restore me"
    finally:
        os.remove(dest)


def test_restore_missing_backup():
    mgr = BackupManager()
    engine = RestoreEngine(mgr)
    result = engine.restore("unknown", "/tmp/x", b"data")
    assert result.success is False
    assert result.message == "backup not found"


def test_restore_checksum_mismatch():
    mgr = BackupManager()
    engine = RestoreEngine(mgr)
    record = mgr.create_backup(b"original")
    result = engine.restore(record.backup_id, "/tmp/x", b"corrupted")
    assert result.success is False
    assert result.message == "checksum mismatch"


def test_validate():
    mgr = BackupManager()
    engine = RestoreEngine(mgr)
    record = mgr.create_backup(b"abc")
    assert engine.validate(record.backup_id, b"abc") is True
    assert engine.validate(record.backup_id, b"def") is False


def test_list_restore_points():
    mgr = BackupManager()
    engine = RestoreEngine(mgr)
    record = mgr.create_backup(b"p1")
    engine.restore(record.backup_id, "/tmp/x", b"p1")
    points = engine.list_restore_points()
    assert len(points) == 1
    assert points[0]["backup_id"] == record.backup_id
    assert points[0]["success"] is True
