"""
Session Persistence - Task 120

Save state and resume after crash with consistency.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SessionState:
    session_id: str
    state: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    checksum: str = ""
    is_completed: bool = False

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        import hashlib
        content = json.dumps(self.state, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def verify_checksum(self) -> bool:
        return self._compute_checksum() == self.checksum


class SessionPersistence:
    """
    Manages session persistence with crash recovery.
    
    Features:
    - Atomic state saves
    - Checksum validation
    - Crash recovery
    - Consistency guarantees
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            storage_dir = os.path.join(tempfile.gettempdir(), "astrovox_sessions")
        self.storage_dir = storage_dir
        self._lock = threading.RLock()
        self._states: Dict[str, SessionState] = {}
        self._history: Dict[str, List[SessionState]] = {}
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_file_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"{session_id}.json")

    def save_state(self, session_id: str, state: Dict[str, Any]) -> SessionState:
        """
        Save session state atomically.
        
        Uses write-to-temp-then-rename for atomicity.
        """
        with self._lock:
            now = datetime.utcnow()
            session_state = SessionState(
                session_id=session_id,
                state=copy.deepcopy(state),
                updated_at=now,
            )
            
            file_path = self._get_file_path(session_id)
            temp_path = file_path + ".tmp"
            
            with open(temp_path, "w") as f:
                json.dump(asdict(session_state), f, indent=2, default=str)
            
            os.replace(temp_path, file_path)
            
            self._states[session_id] = session_state
            if session_id not in self._history:
                self._history[session_id] = []
            self._history[session_id].append(session_state)
            
            return session_state

    def load_state(self, session_id: str) -> Optional[SessionState]:
        """Load session state from disk."""
        with self._lock:
            file_path = self._get_file_path(session_id)
            if not os.path.exists(file_path):
                return None
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                
                session_state = SessionState(
                    session_id=data["session_id"],
                    state=data["state"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    checksum=data.get("checksum", ""),
                    is_completed=data.get("is_completed", False),
                )
                
                if not session_state.verify_checksum():
                    raise ValueError(f"Checksum mismatch for session {session_id}")
                
                self._states[session_id] = session_state
                return session_state
                
            except (json.JSONDecodeError, KeyError, ValueError):
                return None

    def resume_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Resume a session after crash.
        
        Returns state dict if resumable, None if corrupted or completed.
        """
        with self._lock:
            session_state = self.load_state(session_id)
            if session_state is None:
                return None
            if session_state.is_completed:
                return None
            return copy.deepcopy(session_state.state)

    def complete_session(self, session_id: str, final_state: Optional[Dict[str, Any]] = None) -> bool:
        """Mark session as completed and persist final state."""
        with self._lock:
            if final_state is not None:
                self.save_state(session_id, final_state)
            session_state = self._states.get(session_id)
            if session_state:
                session_state.is_completed = True
                file_path = self._get_file_path(session_id)
                with open(file_path, "w") as f:
                    json.dump(asdict(session_state), f, indent=2, default=str)
                return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its history."""
        with self._lock:
            file_path = self._get_file_path(session_id)
            if os.path.exists(file_path):
                os.remove(file_path)
            self._states.pop(session_id, None)
            self._history.pop(session_id, None)
            return True

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the history of state changes for a session."""
        with self._lock:
            history = self._history.get(session_id, [])
            return [
                {
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                    "checksum": s.checksum,
                    "is_completed": s.is_completed,
                }
                for s in history
            ]

    def list_sessions(self) -> List[str]:
        """List all persisted session IDs."""
        with self._lock:
            sessions = []
            for f in os.listdir(self.storage_dir):
                if f.endswith(".json"):
                    sessions.append(f[:-5])
            return sessions

    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics."""
        with self._lock:
            return {
                "total_sessions": len(self._states),
                "storage_dir": self.storage_dir,
                "completed_sessions": sum(1 for s in self._states.values() if s.is_completed),
                "active_sessions": sum(1 for s in self._states.values() if not s.is_completed),
            }
