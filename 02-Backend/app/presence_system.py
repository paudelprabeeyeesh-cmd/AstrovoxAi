"""Presence system for online status."""

from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class PresenceStatus(Enum):
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class Presence:
    user_id: str
    status: PresenceStatus
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class PresenceManager:
    _presences: Dict[str, Presence] = {}
    _user_sessions: Dict[str, Set[str]] = {}

    @classmethod
    def set_presence(cls, user_id: str, status: PresenceStatus, metadata: Optional[Dict[str, Any]] = None) -> Presence:
        presence = Presence(
            user_id=user_id,
            status=status,
            metadata=metadata or {},
        )
        cls._presences[user_id] = presence
        return presence

    @classmethod
    def get_presence(cls, user_id: str) -> Optional[Presence]:
        return cls._presences.get(user_id)

    @classmethod
    def get_bulk_presence(cls, user_ids: List[str]) -> Dict[str, Optional[Presence]]:
        return {uid: cls._presences.get(uid) for uid in user_ids}

    @classmethod
    def list_online_users(cls) -> List[str]:
        return [uid for uid, p in cls._presences.items() if p.status == PresenceStatus.ONLINE]

    @classmethod
    def update_heartbeat(cls, user_id: str) -> None:
        presence = cls._presences.get(user_id)
        if presence:
            presence.last_seen = datetime.now(timezone.utc)
