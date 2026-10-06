"""User profiles: per-user preferences, history, and settings."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class UserProfile:
    """A user profile with preferences and history."""
    user_id: str
    name: str = "Anonymous"
    email: str = ""
    preferences: dict = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    created: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def set_preference(self, key: str, value: Any) -> None:
        self.preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.preferences.get(key, default)

    def append_history(self, event: str, **context) -> dict:
        entry = {"event": event, "context": context,
                 "timestamp": time.time()}
        self.history.append(entry)
        self.last_active = time.time()
        return entry

    def to_dict(self) -> dict:
        return {"user_id": self.user_id, "name": self.name, "email": self.email,
                "preferences": self.preferences, "history": self.history,
                "created": self.created, "last_active": self.last_active,
                "metadata": self.metadata}

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        d = d.copy()
        d.setdefault("created", time.time())
        d.setdefault("last_active", time.time())
        d.setdefault("preferences", {})
        d.setdefault("history", [])
        return cls(**d)


class UserProfileStore:
    """Persistent store of user profiles."""

    def __init__(self, path: str = "data/user_profiles.json"):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
            self._profiles: dict[str, UserProfile] = {
                p["user_id"]: UserProfile.from_dict(p) for p in data}
        except Exception:
            self._profiles = {}

    def _save(self) -> None:
        self._path.write_text(json.dumps([p.to_dict() for p in self._profiles.values()]))

    def get(self, user_id: str) -> UserProfile | None:
        return self._profiles.get(user_id)

    def create(self, user_id: str, name: str = "Anonymous") -> UserProfile:
        profile = UserProfile(user_id=user_id, name=name)
        self._profiles[user_id] = profile
        self._save()
        return profile

    def update(self, user_id: str, name: str | None = None,
               preferences: dict | None = None) -> UserProfile | None:
        profile = self.get(user_id)
        if profile is None:
            return None
        if name is not None:
            profile.name = name
        if preferences is not None:
            profile.preferences.update(preferences)
        profile.last_active = time.time()
        self._save()
        return profile

    def history(self, user_id: str, event: str | None = None, limit: int = 20) -> list[dict]:
        profile = self.get(user_id)
        if profile is None:
            return []
        if event is None:
            return profile.history[-limit:]
        return [e for e in profile.history if e.get("event") == event][-limit:]

    def set_preference(self, user_id: str, key: str, value: Any) -> bool:
        profile = self.get(user_id)
        if profile is None:
            return False
        profile.set_preference(key, value)
        self._save()
        return True

    def delete(self, user_id: str) -> bool:
        if user_id in self._profiles:
            del self._profiles[user_id]
            self._save()
            return True
        return False

    def list_users(self) -> list[str]:
        return list(self._profiles.keys())
