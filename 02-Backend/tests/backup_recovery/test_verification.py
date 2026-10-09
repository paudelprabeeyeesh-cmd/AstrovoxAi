from backup_recovery.verification import BackupVerifier, VerificationResult
from backup_recovery.snapshot_manager import Snapshot, SnapshotManager
from backup_recovery.incremental_backup import IncrementalBackup, IncrementalBackupManager


def test_verify_snapshot_valid():
    manager = SnapshotManager()
    data = b"hello world"
    snapshot = manager.create_snapshot(data)
    result = BackupVerifier.verify_snapshot(snapshot, data)
    assert result.verified is True
    assert "valid" in result.message


def test_verify_snapshot_invalid_checksum():
    manager = SnapshotManager()
    snapshot = manager.create_snapshot(b"hello")
    result = BackupVerifier.verify_snapshot(snapshot, b"world")
    assert result.verified is False
    assert "checksum" in result.message.lower()


def test_verify_snapshot_invalid_size():
    manager = SnapshotManager()
    snapshot = manager.create_snapshot(b"hello")
    result = BackupVerifier.verify_snapshot(snapshot, b"hello world")
    assert result.verified is False
    assert "size" in result.message.lower()


def test_verify_incremental_backup_valid():
    inc_manager = IncrementalBackupManager()
    backup_id = inc_manager.start_backup(label="test")
    inc_manager.record_changes(backup_id, [b"c1"])
    inc_manager.complete_backup(backup_id)
    backup = inc_manager.get_backup(backup_id)
    result = BackupVerifier.verify_incremental_backup(backup)
    assert result.verified is True
    assert "valid" in result.message


def test_verify_incremental_backup_not_completed():
    inc_manager = IncrementalBackupManager()
    backup_id = inc_manager.start_backup(label="test")
    backup = inc_manager.get_backup(backup_id)
    result = BackupVerifier.verify_incremental_backup(backup)
    assert result.verified is False
    assert "not completed" in result.message


def test_verify_incremental_backup_invalid_size():
    inc_manager = IncrementalBackupManager()
    backup_id = inc_manager.start_backup(label="test")
    inc_manager.record_changes(backup_id, [b"c1"])
    inc_manager.complete_backup(backup_id)
    backup = inc_manager.get_backup(backup_id)
    backup.metadata["total_size"] = 9999
    result = BackupVerifier.verify_incremental_backup(backup)
    assert result.verified is False
    assert "size" in result.message.lower()


def test_verify_checksum_valid():
    data = b"hello"
    result = BackupVerifier.verify_checksum(data, __import__("hashlib").sha256(data).hexdigest())
    assert result.verified is True
    assert "valid" in result.message


def test_verify_checksum_invalid():
    data = b"hello"
    result = BackupVerifier.verify_checksum(data, "invalid_checksum")
    assert result.verified is False
    assert "mismatch" in result.message
