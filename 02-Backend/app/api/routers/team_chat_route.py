"""Team Chat API — channels, messages, reactions, direct messages."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel

from app.collaboration_platform import (
    ChatChannelType,
    CollaborationService,
)
from app.utils.auth.auth_utils import get_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/team-chat", tags=["team-chat"])
service = CollaborationService()


# ============================================================================
# Request Models
# ============================================================================


class CreateChannelRequest(BaseModel):
    name: str
    channel_type: str = "team"
    member_ids: Optional[list[str]] = None
    is_private: bool = False


class SendMessageRequest(BaseModel):
    channel_id: str
    content: str


class DirectMessageRequest(BaseModel):
    recipient_id: str
    content: str


# ============================================================================
# Channels
# ============================================================================


@router.post("/channels")
async def create_channel(
    workspace_id: str,
    request: CreateChannelRequest,
    authorization: str = Header(None),
):
    """Create a team chat channel."""
    user_id = get_user_id_from_token(authorization)
    try:
        channel_type = ChatChannelType(request.channel_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid channel type")

    channel = service.create_team_chat(
        workspace_id=workspace_id,
        name=request.name,
        user_id=user_id,
        members=request.member_ids,
    )
    channel.channel_type = channel_type
    channel.is_private = request.is_private
    return {
        "status": "OK",
        "channel": {
            "id": channel.id,
            "name": channel.name,
            "channel_type": channel.channel_type.value,
            "members": channel.members,
            "is_private": channel.is_private,
            "created_at": channel.created_at,
        },
    }


@router.get("/channels")
async def list_channels(
    workspace_id: str,
    authorization: str = Header(None),
):
    """List chat channels in a workspace."""
    user_id = get_user_id_from_token(authorization)
    channels = service.team_chat.list_channels(workspace_id)
    return {
        "status": "OK",
        "channels": [
            {
                "id": c.id,
                "name": c.name,
                "channel_type": c.channel_type.value,
                "members": c.members,
                "is_private": c.is_private,
                "created_at": c.created_at,
            }
            for c in channels
        ],
    }


@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str, authorization: str = Header(None)):
    """Get channel details."""
    get_user_id_from_token(authorization)
    channel = service.team_chat.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return {
        "status": "OK",
        "channel": {
            "id": channel.id,
            "name": channel.name,
            "channel_type": channel.channel_type.value,
            "members": channel.members,
            "is_private": channel.is_private,
            "created_by": channel.created_by,
            "created_at": channel.created_at,
        },
    }


# ============================================================================
# Messages
# ============================================================================


@router.post("/messages")
async def send_message(
    request: SendMessageRequest,
    authorization: str = Header(None),
):
    """Send a message to a channel."""
    user_id = get_user_id_from_token(authorization)
    message = service.send_team_message(request.channel_id, user_id, request.content)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return {
        "status": "OK",
        "message": {
            "id": message.id,
            "channel_id": message.channel_id,
            "user_id": message.user_id,
            "content": message.content,
            "created_at": message.created_at,
        },
    }


@router.get("/channels/{channel_id}/messages")
async def get_channel_messages(
    channel_id: str,
    authorization: str = Header(None),
    limit: int = Query(default=50, le=200),
    before: float = Query(default=0.0),
):
    """Get messages in a channel."""
    get_user_id_from_token(authorization)
    messages = service.team_chat.get_messages(channel_id, limit=limit, before=before)
    return {
        "status": "OK",
        "messages": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "content": m.content,
                "created_at": m.created_at,
                "edited_at": m.edited_at,
                "is_pinned": m.is_pinned,
                "reactions": m.reactions,
            }
            for m in messages
        ],
    }


@router.post("/messages/{message_id}/react")
async def react_to_message(
    message_id: str,
    channel_id: str,
    emoji: str,
    authorization: str = Header(None),
):
    """React to a message."""
    user_id = get_user_id_from_token(authorization)
    if not service.team_chat.add_reaction(message_id, channel_id, user_id, emoji):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return {"status": "OK"}


@router.post("/messages/{message_id}/pin")
async def pin_message(message_id: str, channel_id: str, authorization: str = Header(None)):
    """Pin or unpin a message."""
    get_user_id_from_token(authorization)
    if not service.team_chat.pin_message(message_id, channel_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return {"status": "OK"}


# ============================================================================
# Direct Messages
# ============================================================================


@router.get("/direct/{user_id}/channels")
async def get_direct_channel(
    user_id: str,
    authorization: str = Header(None),
):
    """Get or create a direct message channel between two users."""
    caller_id = get_user_id_from_token(authorization)
    channels = service.team_chat.list_channels("")
    existing = next(
        (
            c for c in channels
            if c.channel_type == ChatChannelType.DIRECT
            and set(c.members) == {caller_id, user_id}
        ),
        None,
    )
    if existing:
        return {"status": "OK", "channel_id": existing.id}
    channel = service.create_team_chat(
        workspace_id="",
        name=f"DM: {caller_id} <-> {user_id}",
        created_by=caller_id,
        members=[caller_id, user_id],
    )
    channel.channel_type = ChatChannelType.DIRECT
    return {
        "status": "OK",
        "channel": {
            "id": channel.id,
            "name": channel.name,
            "channel_type": channel.channel_type.value,
            "members": channel.members,
            "created_at": channel.created_at,
        },
    }
