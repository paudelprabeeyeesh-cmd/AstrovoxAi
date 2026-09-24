"""
User Memory - Aggregated per-user memory profile.

Synthesizes information from all memory layers into a coherent user profile:
- Preferences
- Personal facts
- Workflow patterns
- Interaction history
- Goals and motivations
"""

from typing import Any, Dict, List, Optional
from datetime import datetime


class UserMemory:
    """Aggregated memory profile for a user."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.profile: Dict[str, Any] = {
            "user_id": user_id,
            "preferences": {},
            "personal_facts": {},
            "workflows": {},
            "goals": [],
            "last_updated": datetime.utcnow().isoformat(),
        }
        self._history: List[Dict[str, Any]] = []

    def update_preference(self, key: str, value: Any, confidence: float = 0.8):
        self.profile["preferences"][key] = {
            "value": value,
            "confidence": confidence,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._record_update("preference", key, value)

    def update_personal_fact(self, key: str, value: Any, confidence: float = 0.8):
        self.profile["personal_facts"][key] = {
            "value": value,
            "confidence": confidence,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._record_update("personal_fact", key, value)

    def update_workflow(self, key: str, value: Any):
        self.profile["workflows"][key] = {
            "value": value,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._record_update("workflow", key, value)

    def add_goal(self, goal: str, priority: float = 0.5):
        self.profile["goals"].append({
            "goal": goal,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        })

    def get_profile(self) -> Dict[str, Any]:
        return dict(self.profile)

    def get_preferences(self) -> Dict[str, Any]:
        return {k: v["value"] for k, v in self.profile.get("preferences", {}).items()}

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._history[-limit:]

    def _record_update(self, update_type: str, key: str, value: Any):
        self._history.append({
            "type": update_type,
            "key": key,
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.profile["last_updated"] = datetime.utcnow().isoformat()
