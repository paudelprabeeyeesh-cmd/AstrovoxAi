"""AI collaboration chat."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIChatMessage:
    message_id: str
    channel_id: str
    user_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AICollaborationChat:
    def __init__(self) -> None:
        self._channels: Dict[str, List[AIChatMessage]] = {}

    def send_message(self, channel_id: str, user_id: str, content: str) -> AIChatMessage:
        message = AIChatMessage(message_id=uuid.uuid4().hex, channel_id=channel_id, user_id=user_id, content=content)
        self._channels.setdefault(channel_id, []).append(message)
        return message


ai_collaboration_chat = AICollaborationChat()
