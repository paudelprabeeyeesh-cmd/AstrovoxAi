"""
Session Persistence - product_polish

File-backed session state persistence with checksum validation.
"""

import copy
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SessionState:
    session_id: str
    state: Dict[str, Any]
    checksum: str = ""
    created_at: str = ""
    updated_at: str = ""
    is_completed: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = self._now()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.checksum:
            self.checksum = self._compute_checksum()

    @staticmethod
    def _now() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def _compute_checksum(self) -> str:
        content = json.dumps(self.state, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def verify_checksum(self) -> bool:
        return self.checksum == self._compute_checksum()


class SessionPersistence:
    def __init__(self, storage_dir: str) -> None:
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._states: Dict[str, SessionState] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}

    def _path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"{session_id}.json")

    def save_state(self, session_id: str, state: Dict[str, Any]) -> SessionState:
        path = self._path(session_id)
        now = SessionState._now()
        if session_id in self._states:
            existing = self._states[session_id]
            existing.state = copy.deepcopy(state)
            existing.updated_at = now
            existing.checksum = existing._compute_checksum()
        else:
            existing = SessionState(session_id=session_id, state=copy.deepcopy(state), created_at=now, updated_at=now)
        self._states[session_id] = existing
        self._history.setdefault(session_id, []).append({
            "created_at": existing.created_at,
            "updated_at": existing.updated_at,
            "checksum": existing.checksum,
            "is_completed": existing.is_completed,
        })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing.__dict__, f, default=str)
        return existing

    def load_state(self, session_id: str) -> Optional[SessionState]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = SessionState(**data)
            self._states[session_id] = state
            return state
        except (json.JSONDecodeError, TypeError):
            return None

    def resume_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        state = self.load_state(session_id)
        if state is None or state.is_completed:
            return None
        return copy.deepcopy(state.state)

    def complete_session(self, session_id: str, final_state: Optional[Dict[str, Any]] = None) -> bool:
        state = self._states.get(session_id)
        if state is None:
            state = self.load_state(session_id)
        if state is None:
            return False
        if final_state is not None:
            state.state = copy.deepcopy(final_state)
            state.checksum = state._compute_checksum()
        state.is_completed = True
        state.updated_at = SessionState._now()
        self._states[session_id] = state
        path = self._path(session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state.__dict__, f, default=str)
        return True

    def delete_session(self, session_id: str) -> bool:
        path = self._path(session_id)
        if os.path.exists(path):
            os.remove(path)
        self._states.pop(session_id, None)
        self._history.pop(session_id, None)
        return True

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._history.get(session_id, []))

    def list_sessions(self) -> List[str]:
        return sorted([f for f in os.listdir(self.storage_dir) if f.endswith(".json")])

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._states)
        completed = sum(1 for s in self._states.values() if s.is_completed)
        return {
            "total_sessions": total,
            "completed_sessions": completed,
            "active_sessions": total - completed,
        }
