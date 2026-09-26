"""Episodic memory for conversation history."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid


class EventType(Enum):
    CONVERSATION = "conversation"
    TASK_COMPLETION = "task_completion"
    ERROR = "error"
    MILESTONE = "milestone"
    INTERACTION = "interaction"
    ACHIEVEMENT = "achievement"


@dataclass
class Episode:
    episode_id: str
    user_id: str
    session_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EpisodicMemory:
    _episodes: Dict[str, Episode] = {}

    @classmethod
    def store(cls, user_id: str, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Episode:
        episode_id = str(uuid.uuid4())
        episode = Episode(
            episode_id=episode_id,
            user_id=user_id,
            session_id=session_id,
            content=content,
            metadata=metadata or {},
        )
        cls._episodes[episode_id] = episode
        return episode

    @classmethod
    def get(cls, episode_id: str) -> Optional[Episode]:
        return cls._episodes.get(episode_id)

    @classmethod
    def get_user_episodes(cls, user_id: str, limit: int = 100) -> List[Episode]:
        return [e for e in cls._episodes.values() if e.user_id == user_id][:limit]

    @classmethod
    def get_session_episodes(cls, session_id: str) -> List[Episode]:
        return [e for e in cls._episodes.values() if e.session_id == session_id]
