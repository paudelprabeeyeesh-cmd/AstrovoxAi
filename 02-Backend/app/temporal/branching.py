"""Branch and branching timeline management.

Provides:
- Timeline creation and management
- Branch creation from points in time
- Branch merging
- Branch comparison
- Branch visualization
"""

from __future__ import annotations

import copy
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BranchStatus(Enum):
    """Branch status."""

    ACTIVE = "active"
    MERGED = "merged"
    ABANDONED = "abandoned"
    CONFLICTED = "conflicted"


class BranchType(Enum):
    """Branch type."""

    TIMELINE = "timeline"
    EXPERIMENT = "experiment"
    HOTFIX = "hotfix"
    FEATURE = "feature"


@dataclass
class Branch:
    """Timeline branch."""

    branch_id: str
    name: str
    branch_type: BranchType
    parent_branch_id: Optional[str]
    parent_snapshot_id: str
    parent_version: int
    fork_timestamp: datetime
    status: BranchStatus = BranchStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    merged_at: Optional[datetime] = None
    merged_into: Optional[str] = None


@dataclass
class TimelineBranch:
    """Timeline branch wrapper with state."""

    branch: Branch
    snapshots: List[Any] = field(default_factory=list)
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    head_version: int = 0


class BranchTimelineManager:
    """Timeline branch manager.

    Provides:
    - Branch creation and management
    - Branch merging
    - Branch comparison
    - Branch visualization data
    """

    def __init__(self) -> None:
        self._branches: Dict[str, TimelineBranch] = {}
        self._main_branch_id: Optional[str] = None
        self._lock = False

    def create_branch(
        self,
        name: str,
        branch_type: BranchType,
        parent_snapshot_id: str,
        parent_version: int,
        parent_branch_id: Optional[str] = None,
        fork_timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Branch:
        branch = Branch(
            branch_id=str(uuid.uuid4()),
            name=name,
            branch_type=branch_type,
            parent_branch_id=parent_branch_id,
            parent_snapshot_id=parent_snapshot_id,
            parent_version=parent_version,
            fork_timestamp=fork_timestamp or datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        timeline_branch = TimelineBranch(branch=branch, head_version=parent_version)
        self._branches[branch.branch_id] = timeline_branch
        return branch

    def get_branch(self, branch_id: str) -> Optional[Branch]:
        tb = self._branches.get(branch_id)
        return tb.branch if tb else None

    def get_branch_state(self, branch_id: str) -> Optional[TimelineBranch]:
        return self._branches.get(branch_id)

    def append_snapshot(self, branch_id: str, snapshot: Any) -> bool:
        tb = self._branches.get(branch_id)
        if not tb:
            return False
        tb.snapshots.append(snapshot)
        tb.head_version = getattr(snapshot, "version", tb.head_version + 1)
        return True

    def record_state(self, branch_id: str, state: Dict[str, Any]) -> bool:
        tb = self._branches.get(branch_id)
        if not tb:
            return False
        tb.state_history.append(copy.deepcopy(state))
        return True

    def merge(
        self,
        source_branch_id: str,
        target_branch_id: str,
        merge_timestamp: Optional[datetime] = None,
    ) -> Branch:
        source = self._branches.get(source_branch_id)
        target = self._branches.get(target_branch_id)
        if not source or not target:
            raise ValueError("invalid branch ID")

        merged_branch = Branch(
            branch_id=str(uuid.uuid4()),
            name=f"merge:{source.branch.name}->{target.branch.name}",
            branch_type=BranchType.TIMELINE,
            parent_branch_id=source.branch.parent_branch_id,
            parent_snapshot_id=source.branch.parent_snapshot_id,
            parent_version=source.branch.parent_version,
            fork_timestamp=datetime.now(timezone.utc),
            status=BranchStatus.MERGED,
            merged_at=merge_timestamp or datetime.now(timezone.utc),
            merged_into=target.branch.branch_id,
        )
        source.branch.status = BranchStatus.MERGED
        source.branch.merged_into = target.branch.branch_id
        source.branch.merged_at = merged_branch.merged_at
        return merged_branch

    def compare(self, branch_a_id: str, branch_b_id: str) -> Dict[str, Any]:
        tb_a = self._branches.get(branch_a_id)
        tb_b = self._branches.get(branch_b_id)
        if not tb_a or not tb_b:
            raise ValueError("invalid branch ID")

        snapshots_a = {getattr(s, "snapshot_id", str(i)): s for i, s in enumerate(tb_a.snapshots)}
        snapshots_b = {getattr(s, "snapshot_id", str(i)): s for i, s in enumerate(tb_b.snapshots)}
        common_ids = set(snapshots_a.keys()) & set(snapshots_b.keys())

        return {
            "branch_a": branch_a_id,
            "branch_b": branch_b_id,
            "total_snapshots_a": len(tb_a.snapshots),
            "total_snapshots_b": len(tb_b.snapshots),
            "common_snapshots": len(common_ids),
            "only_in_a": len(snapshots_a) - len(common_ids),
            "only_in_b": len(snapshots_b) - len(common_ids),
            "divergence_point": tb_a.branch.fork_timestamp.isoformat(),
        }

    def get_branch_history(self, branch_id: str) -> List[Dict[str, Any]]:
        tb = self._branches.get(branch_id)
        if not tb:
            return []
        return [
            {
                "snapshot_id": getattr(s, "snapshot_id", str(i)),
                "version": getattr(s, "version", i),
                "created_at": getattr(s, "created_at", datetime.now(timezone.utc)).isoformat(),
                "state": tb.state_history[i] if i < len(tb.state_history) else {},
            }
            for i, s in enumerate(tb.snapshots)
        ]

    def get_main_branch(self) -> Optional[str]:
        return self._main_branch_id

    def set_main_branch(self, branch_id: str) -> None:
        self._main_branch_id = branch_id

    def list_branches(self) -> List[Branch]:
        return [tb.branch for tb in self._branches.values()]

    def get_visualization(self) -> Dict[str, Any]:
        nodes = []
        edges = []
        for tb in self._branches.values():
            nodes.append({
                "id": tb.branch.branch_id,
                "name": tb.branch.name,
                "type": tb.branch.branch_type.value,
                "status": tb.branch.status.value,
                "fork_timestamp": tb.branch.fork_timestamp.isoformat(),
            })
            if tb.branch.parent_branch_id:
                edges.append({
                    "source": tb.branch.parent_branch_id,
                    "target": tb.branch.branch_id,
                    "type": "forks_from",
                })
        return {
            "nodes": nodes,
            "edges": edges,
            "main_branch": self._main_branch_id,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_branches": len(self._branches),
            "active_branches": sum(1 for tb in self._branches.values() if tb.branch.status == BranchStatus.ACTIVE),
            "merged_branches": sum(1 for tb in self._branches.values() if tb.branch.status == BranchStatus.MERGED),
        }


class TimelineManager:
    """High-level timeline manager."""

    def __init__(self) -> None:
        self.branch_manager = BranchTimelineManager()
        self._lock = False

    def create_timeline(self, aggregate_id: str, snapshot_id: str, version: int) -> Branch:
        branch = self.branch_manager.create_branch(
            name=f"timeline:{aggregate_id}",
            branch_type=BranchType.TIMELINE,
            parent_snapshot_id=snapshot_id,
            parent_version=version,
            parent_branch_id=None,
        )
        return branch
