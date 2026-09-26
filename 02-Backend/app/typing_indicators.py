"""Typing indicators for chat."""

from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta


@dataclass
class TypingIndicator:
    user_id: str
    conversation_id: str
    is_typing: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(seconds=5))


class TypingIndicatorManager:
    _indicators: Dict[str, Dict[str, TypingIndicator]] = {}
    _timeout_seconds = 5

    @classmethod
    def set_typing(cls, user_id: str, conversation_id: str, is_typing: bool = True) -> TypingIndicator:
        key = f"{conversation_id}:{user_id}"
        indicator = TypingIndicator(
            user_id=user_id,
            conversation_id=conversation_id,
            is_typing=is_typing,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=cls._timeout_seconds),
        )
        if conversation_id not in cls._indicators:
            cls._indicators[conversation_id] = {}
        cls._indicators[conversation_id][user_id] = indicator
        return indicator

    @classmethod
    def get_typing_users(cls, conversation_id: str) -> List[str]:
        now = datetime.now(timezone.utc)
        indicators = cls._indicators.get(conversation_id, {})
        return [uid for uid, ind in indicators.items() if ind.is_typing and ind.expires_at > now]

    @classmethod
    def clear_expired(cls) -> None:
        now = datetime.now(timezone.utc)
        for conversation_id, indicators in list(cls._indicators.items()):
            expired = [uid for uid, ind in indicators.items() if ind.expires_at <= now]
            for uid in expired:
                del indicators[uid]
