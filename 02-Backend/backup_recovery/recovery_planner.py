from dataclasses import dataclass, field
from typing import List

from backup_recovery.snapshot_manager import Snapshot, SnapshotManager
from backup_recovery.incremental_backup import IncrementalBackup, IncrementalBackupManager


@dataclass
class RecoveryPlan:
    plan_id: str
    target_timestamp: float
    steps: List[str] = field(default_factory=list)
    snapshot: Optional[Snapshot] = None
    incremental_backup: Optional[IncrementalBackup] = None
    metadata: dict = field(default_factory=dict)


class RecoveryPlanner:
    def __init__(self) -> None:
        self._plans: List[RecoveryPlan] = []

    def plan_recovery(
        self,
        target_ts: float,
        manager: SnapshotManager,
    ) -> RecoveryPlan:
        snapshot = manager.point_in_time(target_ts)
        plan = RecoveryPlan(
            plan_id=snapshot.backup_id if snapshot else f"plan_{target_ts}",
            target_timestamp=target_ts,
            snapshot=snapshot,
        )
        if snapshot:
            plan.steps.append(f"snapshot:{snapshot.backup_id}")
            plan.metadata["type"] = "snapshot"
        else:
            plan.steps.append("no_snapshot_available")
            plan.metadata["type"] = "empty"
        self._plans.append(plan)
        return plan

    def plan_incremental_recovery(
        self,
        backup_id: str,
        inc_manager: IncrementalBackupManager,
    ) -> RecoveryPlan:
        backup = inc_manager.get_backup(backup_id)
        plan = RecoveryPlan(
            plan_id=backup_id,
            target_timestamp=backup.end_time or backup.start_time,
            incremental_backup=backup,
        )
        if backup:
            plan.steps.append(f"incremental:{backup.backup_id}")
            plan.metadata["type"] = "incremental"
            plan.metadata["change_count"] = len(backup.changes)
        else:
            plan.steps.append("no_incremental_backup")
            plan.metadata["type"] = "empty"
        self._plans.append(plan)
        return plan
