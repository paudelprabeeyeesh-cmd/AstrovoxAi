"""Real-time Collaboration — WebSocket-powered live cursors, selections, presence,
chat streaming, and operational broadcasts for shared workspaces.

Integrates with CollaborationService and ConnectionManager.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.collaboration_platform import (
    ResourceType,
    CollaborationService,
    LiveCollaboration,
    LiveCollaborationRegistry,
)
from app.realtime import connection_manager

logger = logging.getLogger(__name__)


# ============================================================================
# WebSocket Collaboration Events
# ============================================================================


class CollaborationEventType(str, Enum):
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"
    JOIN = "join"
    LEAVE = "leave"
    EDIT = "edit"
    COMMENT = "comment"
    PRESENCE = "presence"
    TYPING = "typing"
    MESSAGE = "message"
    SYSTEM = "system"


@dataclass
class CollaborationEvent:
    event_type: CollaborationEventType
    user_id: str
    resource_type: ResourceType
    resource_id: str
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# Collaboration WebSocket Gateway
# ============================================================================


class CollaborationWebSocketGateway:
    """Manage WebSocket connections for collaboration features."""

    def __init__(self, service: Optional[CollaborationService] = None):
        self.service = service or CollaborationService()
        self._connections: dict[str, dict] = {}
        self._resource_subscribers: dict[str, set[str]] = defaultdict(set)

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
    ) -> str:
        await websocket.accept()
        conn_id = f"{user_id}:{resource_type.value}:{resource_id}:{time.time()}"
        self._connections[conn_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }
        resource_key = f"{resource_type.value}:{resource_id}"
        self._resource_subscribers[resource_key].add(conn_id)

        session = self.service.get_live_session(resource_type, resource_id)
        session.set_presence(user_id, "online")
        session.log_event("join", user_id, {"conn_id": conn_id})

        await self._broadcast_to_resource(resource_type, resource_id, {
            "type": CollaborationEventType.PRESENCE.value,
            "user_id": user_id,
            "status": "online",
            "participants": session.get_participants(),
        }, exclude=conn_id)

        return conn_id

    def disconnect(self, conn_id: str) -> None:
        conn = self._connections.pop(conn_id, None)
        if not conn:
            return
        resource_key = f"{conn['resource_type'].value}:{conn['resource_id']}"
        self._resource_subscribers[resource_key].discard(conn_id)

        session = self.service.get_live_session(
            conn["resource_type"], conn["resource_id"]
        )
        session.set_presence(conn["user_id"], "offline")
        session.log_event("leave", conn["user_id"], {"conn_id": conn_id})

        asyncio.ensure_future(self._broadcast_to_resource(
            conn["resource_type"], conn["resource_id"], {
                "type": CollaborationEventType.PRESENCE.value,
                "user_id": conn["user_id"],
                "status": "offline",
                "participants": session.get_participants(),
            }
        ))

    async def handle_event(self, conn_id: str, raw_event: dict) -> None:
        conn = self._connections.get(conn_id)
        if not conn:
            return

        event_type = raw_event.get("type")
        user_id = conn["user_id"]
        resource_type = conn["resource_type"]
        resource_id = conn["resource_id"]
        session = self.service.get_live_session(resource_type, resource_id)

        if event_type == CollaborationEventType.CURSOR_MOVE.value:
            x = float(raw_event.get("x", 0))
            y = float(raw_event.get("y", 0))
            session.set_cursor(user_id, x, y)
            await self._broadcast_to_resource(resource_type, resource_id, {
                "type": CollaborationEventType.CURSOR_MOVE.value,
                "user_id": user_id,
                "x": x,
                "y": y,
                "color": LiveCollaboration._color_for(user_id),
            }, exclude=conn_id)

        elif event_type == CollaborationEventType.SELECTION_CHANGE.value:
            start = int(raw_event.get("start", 0))
            end = int(raw_event.get("end", 0))
            session.set_selection(user_id, start, end)
            await self._broadcast_to_resource(resource_type, resource_id, {
                "type": CollaborationEventType.SELECTION_CHANGE.value,
                "user_id": user_id,
                "start": start,
                "end": end,
            }, exclude=conn_id)

        elif event_type == CollaborationEventType.TYPING.value:
            await self._broadcast_to_resource(resource_type, resource_id, {
                "type": CollaborationEventType.TYPING.value,
                "user_id": user_id,
                "is_typing": bool(raw_event.get("is_typing")),
            }, exclude=conn_id)

        elif event_type == CollaborationEventType.COMMENT.value:
            content = str(raw_event.get("content", ""))
            comment = self.service.add_comment(
                resource_type=resource_type,
                resource_id=resource_id,
                author_id=user_id,
                content=content,
            )
            await self._broadcast_to_resource(resource_type, resource_id, {
                "type": CollaborationEventType.COMMENT.value,
                "comment": {
                    "id": comment.id,
                    "author_id": comment.author_id,
                    "content": comment.content,
                    "created_at": comment.created_at,
                    "parent_id": comment.parent_id,
                },
            })

        elif event_type == CollaborationEventType.MESSAGE.value:
            content = str(raw_event.get("content", ""))
            channel_id = str(raw_event.get("channel_id", ""))
            message = self.service.send_team_message(channel_id, user_id, content)
            if message:
                await self._broadcast_to_resource(resource_type, resource_id, {
                    "type": CollaborationEventType.MESSAGE.value,
                    "message": {
                        "id": message.id,
                        "user_id": message.user_id,
                        "content": message.content,
                        "created_at": message.created_at,
                    },
                })

    async def _broadcast_to_resource(
        self,
        resource_type: ResourceType,
        resource_id: str,
        payload: dict,
        exclude: str = "",
    ) -> None:
        resource_key = f"{resource_type.value}:{resource_id}"
        conn_ids = list(self._resource_subscribers.get(resource_key, set()))
        for conn_id in conn_ids:
            if conn_id == exclude:
                continue
            conn = self._connections.get(conn_id)
            if conn:
                try:
                    await conn["websocket"].send_json(payload)
                except Exception:
                    pass

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        for conn in self._connections.values():
            if conn["user_id"] == user_id:
                try:
                    await conn["websocket"].send_json(payload)
                except Exception:
                    pass

    def get_resource_state(
        self,
        resource_type: ResourceType,
        resource_id: str,
    ) -> dict:
        session = self.service.get_live_session(resource_type, resource_id)
        return {
            "cursors": session.get_cursors(),
            "selections": session.get_selections(),
            "participants": session.get_participants(),
        }


# ============================================================================
# WebSocket Route
# ============================================================================


collaboration_ws = CollaborationWebSocketGateway()


async def collaboration_websocket_endpoint(
    websocket: WebSocket,
    resource_type: str,
    resource_id: str,
    token: str = "",
):
    from app.utils.auth.auth_utils import get_user_id_from_token

    try:
        user_id = get_user_id_from_token(f"Bearer {token}")
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    try:
        rtype = ResourceType(resource_type)
    except ValueError:
        await websocket.close(code=4002, reason="Invalid resource type")
        return

    conn_id = await collaboration_ws.connect(websocket, user_id, rtype, resource_id)

    try:
        await websocket.send_json({
            "type": "connected",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "state": collaboration_ws.get_resource_state(rtype, resource_id),
        })

        while True:
            data = await websocket.receive_text()
            try:
                event = json.loads(data)
                await collaboration_ws.handle_event(conn_id, event)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        collaboration_ws.disconnect(conn_id)
    except Exception as exc:
        logger.error("Collaboration WebSocket error: %s", exc)
        collaboration_ws.disconnect(conn_id)
