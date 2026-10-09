from backup_recovery.recovery_planner import RecoveryPlan, RecoveryPlanner
from backup_recovery.snapshot_manager import SnapshotManager
from backup_recovery.incremental_backup import IncrementalBackupManager


def test_plan_recovery_with_snapshot():
    manager = SnapshotManager()
    manager.create_snapshot(b"hello", label="s1")
    manager.create_snapshot(b"world", label="s2")

    planner = RecoveryPlanner()
    plan = planner.plan_recovery(manager.list_snapshots()[0].timestamp, manager)
    assert len(plan.steps) == 1
    assert plan.snapshot is not None
    assert plan.metadata["type"] == "snapshot"


def test_plan_recovery_without_snapshot():
    manager = SnapshotManager()
    planner = RecoveryPlanner()
    plan = planner.plan_recovery(1000.0, manager)
    assert len(plan.steps) == 1
    assert plan.snapshot is None
    assert plan.metadata["type"] == "empty"


def test_plan_incremental_recovery():
    inc_manager = IncrementalBackupManager()
    backup_id = inc_manager.start_backup(label="inc")
    inc_manager.record_changes(backup_id, [b"c1", b"c2"])
    inc_manager.complete_backup(backup_id)

    planner = RecoveryPlanner()
    plan = planner.plan_incremental_recovery(backup_id, inc_manager)
    assert len(plan.steps) == 1
    assert plan.incremental_backup is not None
    assert plan.metadata["type"] == "incremental"


def test_plan_incremental_recovery_not_found():
    inc_manager = IncrementalBackupManager()
    planner = RecoveryPlanner()
    plan = planner.plan_incremental_recovery("nonexistent", inc_manager)
    assert len(plan.steps) == 1
    assert plan.incremental_backup is None
    assert plan.metadata["type"] == "empty"
