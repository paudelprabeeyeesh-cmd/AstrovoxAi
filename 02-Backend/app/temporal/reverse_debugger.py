"""Reverse debugging for AI systems.

Provides:
- Step-through debugging with time slices
- Reverse execution (stepping backward)
- Breakpoints at specific events
- State inspection at any point
- Debug session recording
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


class DebugDirection(Enum):
    """Debug direction."""

    FORWARD = "forward"
    REVERSE = "reverse"


class DebugAction(Enum):
    """Debug action."""

    STEP = "step"
    CONTINUE = "continue"
    BREAKPOINT = "breakpoint"
    PAUSE = "pause"
    STOP = "stop"


class BreakpointType(Enum):
    """Breakpoint type."""

    EVENT = "event"
    VERSION = "version"
    TIMESTAMP = "timestamp"
    CONDITION = "condition"


@dataclass
class TimeSlice:
    """Time slice for reverse debugging."""

    slice_id: str
    timestamp: datetime
    version: int
    event_position: int
    state: Dict[str, Any]
    event: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slice_id": self.slice_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "event_position": self.event_position,
            "state": self.state,
            "event": self.event,
            "metadata": self.metadata,
        }


@dataclass
class Breakpoint:
    """Debug breakpoint."""

    breakpoint_id: str
    breakpoint_type: BreakpointType
    value: Any
    condition: Optional[str] = None
    hit_count: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DebugSession:
    """Debug session."""

    session_id: str
    aggregate_id: str
    direction: DebugDirection
    current_slice: Optional[TimeSlice] = None
    slices: List[TimeSlice] = field(default_factory=list)
    breakpoints: List[Breakpoint] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReverseDebugger:
    """Reverse debugging engine.

    Provides:
    - Time slice recording
    - Step-through forward/reverse
    - Breakpoint management
    - State inspection
    - Debug session recording
    """

    def __init__(self, event_store: Any, snapshot_engine: Any) -> None:
        self.event_store = event_store
        self.snapshot_engine = snapshot_engine
        self._sessions: Dict[str, DebugSession] = {}
        self._lock = False

    def create_session(self, aggregate_id: str, direction: DebugDirection = DebugDirection.FORWARD) -> DebugSession:
        session = DebugSession(
            session_id=str(uuid.uuid4()),
            aggregate_id=aggregate_id,
            direction=direction,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[DebugSession]:
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> Optional[DebugSession]:
        session = self._sessions.pop(session_id, None)
        if session:
            session.ended_at = datetime.now(timezone.utc)
        return session

    def _get_events(self, aggregate_id: str, position: Optional[int] = None) -> List[Any]:
        if self.event_store is None:
            return []
        if position:
            events = self.event_store.get_events(aggregate_id=aggregate_id, limit=position or 1000)
        else:
            events = self.event_store.get_events(aggregate_id=aggregate_id, limit=1000)
        return events

    def record_time_slice(
        self,
        session: DebugSession,
        event_position: int,
        event: Dict[str, Any],
        state: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> TimeSlice:
        slice_obj = TimeSlice(
            slice_id=str(uuid.uuid4()),
            timestamp=timestamp or datetime.now(timezone.utc),
            version=event_position,
            event_position=event_position,
            state=copy.deepcopy(state),
            event=copy.deepcopy(event),
        )
        session.slices.append(slice_obj)
        session.current_slice = slice_obj
        return slice_obj

    def _maybe_hit_breakpoint(self, session: DebugSession, slice_obj: TimeSlice) -> bool:
        for bp in session.breakpoints:
            if not bp.enabled:
                continue
            hit = False
            if bp.breakpoint_type == BreakpointType.EVENT:
                hit = slice_obj.event_position == bp.value
            elif bp.breakpoint_type == BreakpointType.VERSION:
                hit = slice_obj.version == bp.value
            elif bp.breakpoint_type == BreakpointType.TIMESTAMP:
                if isinstance(bp.value, datetime):
                    hit = slice_obj.timestamp == bp.value
            if hit:
                bp.hit_count += 1
                return True
        return False

    def add_breakpoint(self, session_id: str, breakpoint: Breakpoint) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.breakpoints.append(breakpoint)

    def step_forward(self, session: DebugSession, steps: int = 1) -> TimeSlice:
        events = self._get_events(session.aggregate_id)
        current_pos = session.current_slice.event_position if session.current_slice else 0
        target_pos = min(current_pos + steps, len(events))
        event = events[target_pos - 1] if target_pos > 0 else {}
        state = self._reconstruct_state(events[:target_pos])
        slice_obj = self.record_time_slice(session, target_pos, getattr(event, "payload", event), state)
        return slice_obj

    def step_reverse(self, session: DebugSession, steps: int = 1) -> TimeSlice:
        events = self._get_events(session.aggregate_id)
        current_pos = session.current_slice.event_position if session.current_slice else 0
        target_pos = max(current_pos - steps, 0)
        event = events[target_pos - 1] if target_pos > 0 else {}
        state = self._reconstruct_state(events[:target_pos])
        slice_obj = self.record_time_slice(session, target_pos, getattr(event, "payload", event), state)
        return slice_obj

    def _reconstruct_state(self, events: List[Any]) -> Dict[str, Any]:
        state: Dict[str, Any] = {}
        for event in events:
            if hasattr(event, "payload"):
                state = {**state, **event.payload}
        return state

    def get_state_at_slice(self, session: DebugSession, slice_obj: TimeSlice) -> Dict[str, Any]:
        return copy.deepcopy(slice_obj.state)

    def inspect(self, session: DebugSession, path: str = "") -> Any:
        if not session.current_slice:
            return None
        state = copy.deepcopy(session.current_slice.state)
        if not path:
            return state
        parts = path.split(".")
        for part in parts:
            if isinstance(state, dict) and part in state:
                state = state[part]
            else:
                return None
        return state

    def record_session(self, session: DebugSession) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "aggregate_id": session.aggregate_id,
            "direction": session.direction.value,
            "slices": len(session.slices),
            "breakpoints": len(session.breakpoints),
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "metadata": session.metadata,
        }

    def get_sessions(self) -> List[str]:
        return list(self._sessions.keys())

    def delete_session(self, session_id: str) -> bool:
        return session_id in self._sessions.pop(session_id, None)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "total_slices": sum(len(s.slices) for s in self._sessions.values()),
        }


class TimeTravelDebugger:
    """High-level time-travel debugger."""

    def __init__(self, event_store: Any, snapshot_engine: Any) -> None:
        self.reverse_debugger = ReverseDebugger(event_store, snapshot_engine)
        self._lock = False

    def time_travel(
        self,
        aggregate_id: str,
        version: int,
        action: Optional[DebugAction] = None,
        direction: Optional[DebugDirection] = None,
    ) -> Dict[str, Any]:
        session = self.reverse_debugger.create_session(aggregate_id, direction or DebugDirection.FORWARD)
        if action == DebugAction.STEP:
            slice_obj = self.reverse_debugger.step_forward(session, 1)
        elif direction == DebugDirection.REVERSE:
            slice_obj = self.reverse_debugger.step_reverse(session, 1)
        else:
            slice_obj = self.reverse_debugger.step_forward(session, 1)
        return {
            "session_id": session.session_id,
            "slice": slice_obj.to_dict(),
            "action": action.value if action else "unknown",
        }

    def reverse_time(self, aggregate_id: str, steps: int = 1) -> Dict[str, Any]:
        session = self.reverse_debugger.create_session(aggregate_id, DebugDirection.REVERSE)
        slice_obj = self.reverse_debugger.step_reverse(session, steps)
        return {
            "session_id": session.session_id,
            "slice": slice_obj.to_dict(),
            "direction": "reverse",
        }
