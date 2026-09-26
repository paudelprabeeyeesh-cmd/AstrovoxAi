"""Real-time collaboration chat."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    message_id: str
    channel_id: str
    user_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CollaborationChat:
    def __init__(self) -> None:
        self._channels: Dict[str, List[ChatMessage]] = {}

    def send_message(self, channel_id: str, user_id: str, content: str) -> ChatMessage:
        message = ChatMessage(message_id=uuid.uuid4().hex, channel_id=channel_id, user_id=user_id, content=content)
        self._channels.setdefault(channel_id, []).append(message)
        return message

    def get_history(self, channel_id: str, limit: int = 50) -> List[ChatMessage]:
        return self._channels.get(channel_id, [])[-limit:]


collaboration_chat = CollaborationChat()
