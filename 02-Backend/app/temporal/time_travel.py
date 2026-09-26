"""Time-travel debugging for AI systems.

Provides:
- Snapshot-based state capture
- Timeline reconstruction
- Reverse debugging
- Branch visualization
- Time-travel query interface
- Historical state comparison
- Temporal breakpoints
"""

from __future__ import annotations

import copy
import difflib
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


class BreakpointType(str, Enum):
    TIME = "time"
    POSITION = "position"
    STATE_CHANGE = "state_change"
    EVENT_TYPE = "event_type"
    CONDITION = "condition"


class Direction(str, Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    PAUSE = "pause"


@dataclass(frozen=True)
class TemporalBreakpoint:
    breakpoint_id: str
    breakpoint_type: BreakpointType
    target: Any
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    enabled: bool = True
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StateSnapshot:
    snapshot_id: str
    timestamp: datetime
    position: int
    state: Dict[str, Any]
    parent_snapshot_id: Optional[str]
    branch_id: str
    event_id: Optional[str] = None
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "position": self.position,
            "state": self.state,
            "parent_snapshot_id": self.parent_snapshot_id,
            "branch_id": self.branch_id,
            "event_id": self.event_id,
            "label": self.label,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class TimelineBranch:
    branch_id: str
    name: str
    root_snapshot_id: str
    created_at: datetime
    created_by: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TimelineEvent:
    event_id: str
    timestamp: datetime
    position: int
    event_type: str
    payload: Dict[str, Any]
    branch_id: str
    snapshot_id: Optional[str] = None
    causation_id: Optional[str] = None
    correlation_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Snapshot store
# ---------------------------------------------------------------------------


class SnapshotStore:
    """In-memory snapshot storage with history tracking."""

    def __init__(self) -> None:
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._branch_index: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def store(self, snapshot: StateSnapshot) -> None:
        with self._lock:
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._branch_index.setdefault(snapshot.branch_id, []).append(snapshot.snapshot_id)
            logger.debug("stored snapshot %s on branch %s", snapshot.snapshot_id, snapshot.branch_id)

    def get(self, snapshot_id: str) -> Optional[StateSnapshot]:
        return self._snapshots.get(snapshot_id)

    def list_by_branch(self, branch_id: str) -> List[StateSnapshot]:
        ids = self._branch_index.get(branch_id, [])
        return [self._snapshots[sid] for sid in ids if sid in self._snapshots]

    def latest(self, branch_id: str) -> Optional[StateSnapshot]:
        snaps = self.list_by_branch(branch_id)
        return max(snaps, key=lambda s: s.position) if snaps else None

    def all(self) -> List[StateSnapshot]:
        return list(self._snapshots.values())


# ---------------------------------------------------------------------------
# State differ
# ---------------------------------------------------------------------------


class StateDiffer:
    """Compute diffs between historical states."""

    @staticmethod
    def diff(state_a: Dict[str, Any], state_b: Dict[str, Any]) -> Dict[str, Any]:
        added = {}
        removed = {}
        changed = {}
        unchanged = {}

        all_keys = set(state_a.keys()) | set(state_b.keys())
        for key in sorted(all_keys):
            if key not in state_a:
                added[key] = state_b[key]
            elif key not in state_b:
                removed[key] = state_a[key]
            elif state_a[key] != state_b[key]:
                changed[key] = {"from": state_a[key], "to": state_b[key]}
            else:
                unchanged[key] = state_a[key]

        return {
            "added": added,
            "removed": removed,
            "changed": changed,
            "unchanged": unchanged,
            "summary": {
                "added_count": len(added),
                "removed_count": len(removed),
                "changed_count": len(changed),
                "unchanged_count": len(unchanged),
            },
        }

    @staticmethod
    def unified_diff(state_a: Dict[str, Any], state_b: Dict[str, Any], label_a: str = "before", label_b: str = "after") -> str:
        a_lines = [f"{k}: {StateDiffer._serialize(v)}" for k, v in sorted(state_a.items())]
        b_lines = [f"{k}: {StateDiffer._serialize(v)}" for k, v in sorted(state_b.items())]
        diff = difflib.unified_diff(a_lines, b_lines, fromfile=label_a, tofile=label_b, lineterm="")
        return "\n".join(diff)

    @staticmethod
    def _serialize(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return repr(value)
        return str(value)

    @staticmethod
    def compute_patch(state_a: Dict[str, Any], state_b: Dict[str, Any]) -> List[Dict[str, Any]]:
        patch: List[Dict[str, Any]] = []
        all_keys = set(state_a.keys()) | set(state_b.keys())
        for key in sorted(all_keys):
            if key not in state_a:
                patch.append({"op": "add", "key": key, "value": state_b[key]})
            elif key not in state_b:
                patch.append({"op": "remove", "key": key})
            elif state_a[key] != state_b[key]:
                patch.append({"op": "replace", "key": key, "from": state_a[key], "to": state_b[key]})
        return patch

    @staticmethod
    def apply_patch(state: Dict[str, Any], patch: List[Dict[str, Any]]) -> Dict[str, Any]:
        new_state = copy.deepcopy(state)
        for p in patch:
            op = p["op"]
            key = p["key"]
            if op == "add":
                new_state[key] = p["value"]
            elif op == "remove":
                new_state.pop(key, None)
            elif op == "replace":
                new_state[key] = p["to"]
        return new_state


# ---------------------------------------------------------------------------
# Time-travel debugger
# ---------------------------------------------------------------------------


class TimeTravelDebugger:
    """Main time-travel debugging engine.

    Features:
    - Snapshot-based state capture at any point in time
    - Timeline reconstruction from event history
    - Reverse debugging by stepping back through snapshots
    - Branch visualization for exploring alternative timelines
    - Time-travel query interface
    - Historical state comparison
    - Temporal breakpoints
    """

    def __init__(self, event_store: Any) -> None:
        self._event_store = event_store
        self._snapshots = SnapshotStore()
        self._branches: Dict[str, TimelineBranch] = {}
        self._breakpoints: Dict[str, TemporalBreakpoint] = {}
        self._timeline: List[TimelineEvent] = []
        self._current_branch = "main"
        self._current_position = 0
        self._current_state: Dict[str, Any] = {}
        self._running = False
        self._step_handler: Optional[Callable[[TimelineEvent, Dict[str, Any]], None]] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Branching
    # ------------------------------------------------------------------

    def create_branch(self, name: str, from_snapshot_id: Optional[str] = None, created_by: str = "system") -> str:
        branch_id = f"branch-{uuid.uuid4().hex[:8]}"
        if from_snapshot_id:
            root_id = from_snapshot_id
        else:
            latest = self._snapshots.latest(self._current_branch)
            root_id = latest.snapshot_id if latest else None
            if root_id is None:
                root_id = ""

        branch = TimelineBranch(
            branch_id=branch_id,
            name=name,
            root_snapshot_id=root_id,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
        )
        self._branches[branch_id] = branch
        logger.info("created branch %s from snapshot %s", branch_id, root_id)
        return branch_id

    def switch_branch(self, branch_id: str) -> None:
        if branch_id not in self._branches and branch_id != "main":
            raise ValueError(f"unknown branch: {branch_id}")
        self._current_branch = branch_id
        latest = self._snapshots.latest(branch_id)
        if latest:
            self._current_position = latest.position
            self._current_state = copy.deepcopy(latest.state)
        logger.info("switched to branch %s", branch_id)

    def list_branches(self) -> List[Dict[str, Any]]:
        result = []
        for branch_id, branch in self._branches.items():
            latest = self._snapshots.latest(branch_id)
            result.append({
                "branch_id": branch_id,
                "name": branch.name,
                "root_snapshot_id": branch.root_snapshot_id,
                "latest_position": latest.position if latest else 0,
                "snapshot_count": len(self._snapshots.list_by_branch(branch_id)),
                "created_at": branch.created_at.isoformat(),
                "created_by": branch.created_by,
            })
        return result

    # ------------------------------------------------------------------
    # Snapshot management
    # ------------------------------------------------------------------

    def capture_snapshot(self, state: Dict[str, Any], label: str = "", event_id: Optional[str] = None) -> StateSnapshot:
        snapshot = StateSnapshot(
            snapshot_id=f"snap-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc),
            position=self._current_position,
            state=copy.deepcopy(state),
            parent_snapshot_id=self._snapshots.latest(self._current_branch).snapshot_id if self._snapshots.latest(self._current_branch) else None,
            branch_id=self._current_branch,
            event_id=event_id,
            label=label,
        )
        self._snapshots.store(snapshot)
        logger.debug("captured snapshot %s at position %d", snapshot.snapshot_id, snapshot.position)
        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise ValueError(f"snapshot not found: {snapshot_id}")
        self._current_position = snapshot.position
        self._current_state = copy.deepcopy(snapshot.state)
        self._current_branch = snapshot.branch_id
        logger.info("restored snapshot %s", snapshot_id)
        return copy.deepcopy(self._current_state)

    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self, branch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        branch = branch_id or self._current_branch
        return [s.to_dict() for s in self._snapshots.list_by_branch(branch)]

    # ------------------------------------------------------------------
    # Time-travel queries
    # ------------------------------------------------------------------

    def query_at_position(self, position: int) -> Optional[Dict[str, Any]]:
        candidates = [
            s for s in self._snapshots.all() if s.position <= position
        ]
        if not candidates:
            return None
        snapshot = max(candidates, key=lambda s: s.position)
        return copy.deepcopy(snapshot.state)

    def query_at_time(self, target_time: datetime) -> Optional[Dict[str, Any]]:
        candidates = [
            s for s in self._snapshots.all() if s.timestamp <= target_time
        ]
        if not candidates:
            return None
        snapshot = max(candidates, key=lambda s: s.timestamp)
        return copy.deepcopy(snapshot.state)

    def compare_snapshots(self, snapshot_id_a: str, snapshot_id_b: str) -> Dict[str, Any]:
        snap_a = self._snapshots.get(snapshot_id_a)
        snap_b = self._snapshots.get(snapshot_id_b)
        if snap_a is None or snap_b is None:
            raise ValueError("snapshot not found")
        return StateDiffer.diff(snap_a.state, snap_b.state)

    def compare_positions(self, position_a: int, position_b: int) -> Dict[str, Any]:
        state_a = self.query_at_position(position_a)
        state_b = self.query_at_position(position_b)
        if state_a is None or state_b is None:
            raise ValueError("state not found for one or both positions")
        return StateDiffer.diff(state_a, state_b)

    # ------------------------------------------------------------------
    # Reverse debugging
    # ------------------------------------------------------------------

    def step_forward(self, event: TimelineEvent, apply: Callable[[Dict[str, Any], TimelineEvent], Dict[str, Any]]) -> Dict[str, Any]:
        self._current_state = apply(self._current_state, event)
        self._current_position = event.position
        self._timeline.append(event)
        self._check_breakpoints(event)
        logger.debug("stepped forward to position %d", self._current_position)
        return copy.deepcopy(self._current_state)

    def step_backward(self, steps: int = 1) -> Optional[Dict[str, Any]]:
        if steps < 1:
            return copy.deepcopy(self._current_state)
        target_position = max(0, self._current_position - steps)
        state = self.query_at_position(target_position)
        if state is None:
            return copy.deepcopy(self._current_state)
        self._current_position = target_position
        self._current_state = state
        logger.debug("stepped backward to position %d", self._current_position)
        return copy.deepcopy(self._current_state)

    def reverse_debug_to_position(self, position: int) -> Optional[Dict[str, Any]]:
        return self.step_backward(max(0, self._current_position - position))

    def reverse_debug_to_time(self, target_time: datetime) -> Optional[Dict[str, Any]]:
        state = self.query_at_time(target_time)
        if state is not None:
            self._current_state = state
            self._current_position = min(
                (s.position for s in self._snapshots.all() if s.timestamp <= target_time),
                default=self._current_position,
            )
        return copy.deepcopy(self._current_state)

    # ------------------------------------------------------------------
    # Breakpoints
    # ------------------------------------------------------------------

    def set_breakpoint(self, breakpoint: TemporalBreakpoint) -> None:
        self._breakpoints[breakpoint.breakpoint_id] = breakpoint
        logger.info("set breakpoint %s (%s)", breakpoint.breakpoint_id, breakpoint.breakpoint_type)

    def remove_breakpoint(self, breakpoint_id: str) -> bool:
        if breakpoint_id in self._breakpoints:
            del self._breakpoints[breakpoint_id]
            return True
        return False

    def list_breakpoints(self) -> List[Dict[str, Any]]:
        return [
            {
                "breakpoint_id": bp.breakpoint_id,
                "type": bp.breakpoint_type.value,
                "target": str(bp.target),
                "description": bp.description,
                "enabled": bp.enabled,
                "hit_count": bp.hit_count,
                "created_at": bp.created_at.isoformat(),
            }
            for bp in self._breakpoints.values()
        ]

    def _check_breakpoints(self, event: TimelineEvent) -> Optional[TemporalBreakpoint]:
        for bp in self._breakpoints.values():
            if not bp.enabled:
                continue
            hit = False
            if bp.breakpoint_type == BreakpointType.TIME:
                target_dt = datetime.fromisoformat(bp.target) if isinstance(bp.target, str) else bp.target
                hit = event.timestamp >= target_dt
            elif bp.breakpoint_type == BreakpointType.POSITION:
                hit = event.position >= int(bp.target)
            elif bp.breakpoint_type == BreakpointType.EVENT_TYPE:
                hit = event.event_type == bp.target
            elif bp.breakpoint_type == BreakpointType.STATE_CHANGE:
                hit = bp.condition(self._current_state) if bp.condition else False

            if hit:
                bp.hit_count += 1
                logger.info("breakpoint %s hit at position %d", bp.breakpoint_id, event.position)
                return bp
        return None

    # ------------------------------------------------------------------
    # Branch visualization
    # ------------------------------------------------------------------

    def visualize_branch(self, branch_id: str) -> Dict[str, Any]:
        branch = self._branches.get(branch_id)
        if branch is None and branch_id != "main":
            raise ValueError(f"unknown branch: {branch_id}")
        snapshots = self._snapshots.list_by_branch(branch_id)
        nodes = []
        edges = []
        for snap in sorted(snapshots, key=lambda s: s.position):
            nodes.append({
                "id": snap.snapshot_id,
                "label": snap.label or f"pos-{snap.position}",
                "position": snap.position,
                "timestamp": snap.timestamp.isoformat(),
            })
            if snap.parent_snapshot_id:
                edges.append({"from": snap.parent_snapshot_id, "to": snap.snapshot_id})
        return {
            "branch_id": branch_id,
            "branch_name": branch.name if branch else "main",
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    # ------------------------------------------------------------------
    # Timeline reconstruction
    # ------------------------------------------------------------------

    def reconstruct_timeline(self, event_sequence: List[TimelineEvent]) -> List[Dict[str, Any]]:
        timeline = []
        for event in sorted(event_sequence, key=lambda e: e.position):
            snapshot = self._snapshots.get(event.snapshot_id) if event.snapshot_id else None
            timeline.append({
                "position": event.position,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "snapshot_id": event.snapshot_id,
                "has_snapshot": snapshot is not None,
                "causation_id": event.causation_id,
                "correlation_id": event.correlation_id,
            })
        return timeline

    def build_timeline_from_events(self, events: List[Any]) -> List[TimelineEvent]:
        timeline = []
        for idx, ev in enumerate(events):
            timeline_event = TimelineEvent(
                event_id=getattr(ev, "event_id", f"evt-{uuid.uuid4().hex[:8]}"),
                timestamp=getattr(ev, "occurred_at", datetime.now(timezone.utc)),
                position=idx + 1,
                event_type=getattr(ev, "event_type", str(type(ev).__name__)),
                payload=getattr(ev, "payload", {}),
                branch_id=self._current_branch,
                snapshot_id=None,
                causation_id=getattr(ev, "causation_id", None),
                correlation_id=getattr(ev, "correlation_id", None),
            )
            timeline.append(timeline_event)
        return timeline

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_current_state(self) -> Dict[str, Any]:
        return copy.deepcopy(self._current_state)

    def get_current_position(self) -> int:
        return self._current_position

    def get_current_branch(self) -> str:
        return self._current_branch

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_snapshots": len(self._snapshots.all()),
            "branches": len(self._branches),
            "breakpoints": len(self._breakpoints),
            "timeline_events": len(self._timeline),
            "current_branch": self._current_branch,
            "current_position": self._current_position,
        }


# ---------------------------------------------------------------------------
# Global debugger registry
# ---------------------------------------------------------------------------

_debuggers: Dict[str, TimeTravelDebugger] = {}
_registry_lock = threading.Lock()


def get_debugger(name: str = "default", event_store: Any = None) -> TimeTravelDebugger:
    with _registry_lock:
        if name not in _debuggers:
            store = event_store
            if store is None:
                try:
                    from ..events.event_store import EventStore as _EventStore
                    from ..events.event_store import EventSchemaRegistry
                    store = _EventStore(EventSchemaRegistry())
                except Exception:
                    store = None
            _debuggers[name] = TimeTravelDebugger(store)
        return _debuggers[name]
