"""Real-time chat service with rooms and history."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    message_id: str
    room_id: str
    user_id: str
    content: str
    message_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ChatRoom:
    room_id: str
    name: str
    created_by: str
    members: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ChatService:
    def __init__(self) -> None:
        self._rooms: Dict[str, ChatRoom] = {}
        self._messages: Dict[str, List[ChatMessage]] = {}
        self._typing: Dict[str, Dict[str, float]] = {}

    def create_room(self, name: str, created_by: str, members: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> ChatRoom:
        room_id = str(uuid.uuid4())
        room = ChatRoom(
            room_id=room_id,
            name=name,
            created_by=created_by,
            members=members or [created_by],
            metadata=metadata or {},
        )
        self._rooms[room_id] = room
        self._messages[room_id] = []
        logger.info("Created chat room %s: %s", room_id, name)
        return room

    async def send_message(self, room_id: str, user_id: str, content: str, message_type: str = "text", metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        room = self._rooms.get(room_id)
        if not room:
            raise ValueError(f"Unknown room: {room_id}")
        if user_id not in room.members:
            raise ValueError(f"User {user_id} is not a member of room {room_id}")
        message_id = str(uuid.uuid4())
        message = ChatMessage(
            message_id=message_id,
            room_id=room_id,
            user_id=user_id,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        self._messages.setdefault(room_id, []).append(message)
        return message

    def get_history(self, room_id: str, limit: int = 50, before: Optional[str] = None) -> List[ChatMessage]:
        messages = self._messages.get(room_id, [])
        if before:
            messages = [m for m in messages if m.message_id < before]
        return messages[-limit:]

    def join_room(self, room_id: str, user_id: str) -> ChatRoom:
        room = self._rooms.get(room_id)
        if not room:
            raise ValueError(f"Unknown room: {room_id}")
        if user_id not in room.members:
            room.members.append(user_id)
        return room

    def leave_room(self, room_id: str, user_id: str) -> None:
        room = self._rooms.get(room_id)
        if room and user_id in room.members:
            room.members.remove(user_id)

    def set_typing(self, room_id: str, user_id: str, is_typing: bool) -> None:
        self._typing.setdefault(room_id, {})[user_id] = time.time() if is_typing else 0.0

    def get_typing_users(self, room_id: str) -> List[str]:
        typing = self._typing.get(room_id, {})
        cutoff = time.time() - 3.0
        return [uid for uid, ts in typing.items() if ts > cutoff]

    def list_rooms(self, user_id: str) -> List[ChatRoom]:
        return [room for room in self._rooms.values() if user_id in room.members]


chat_service = ChatService()
