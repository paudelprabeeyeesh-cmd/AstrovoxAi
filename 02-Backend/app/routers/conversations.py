import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import require_verified_email
from ..conversations import (
    create_conversation,
    get_conversation,
    list_conversations,
    search_conversations,
    rename_conversation,
    pin_conversation,
    archive_conversation,
    move_conversation_to_folder,
    delete_conversation,
    add_message,
    get_messages,
    get_recent_messages,
)
from ..schemas import ConversationOut, ConversationUpdate, MessageOut, ConversationSearchOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    title: str | None = None
    model: str = "gpt-4"


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class FolderRequest(BaseModel):
    folder: str = Field(..., min_length=1, max_length=100)


class SendMessageRequest(BaseModel):
    role: str = Field("user", pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=4000)
    model_used: str | None = None
    tokens_used: int | None = Field(None, ge=0)


@router.post("", response_model=ConversationOut)
async def api_create_conversation(
    request: CreateConversationRequest,
    user_id: str = Depends(require_verified_email),
):
    try:
        return create_conversation(user_id, request.title, request.model)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create conversation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("", response_model=list[ConversationOut])
async def api_list_conversations(
    user_id: str = Depends(require_verified_email),
    pinned: bool = Query(False),
    archived: bool = Query(False),
    folder: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    try:
        rows = list_conversations(user_id, pinned_only=pinned, archived_only=archived, folder=folder, limit=limit, offset=offset)
        return [ConversationOut(**r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to list conversations")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/search", response_model=list[ConversationSearchOut])
async def api_search_conversations(
    q: str = Query(..., min_length=1),
    user_id: str = Depends(require_verified_email),
):
    try:
        return search_conversations(user_id, q)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to search conversations")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{conversation_id}", response_model=ConversationOut)
async def api_get_conversation(
    conversation_id: str,
    user_id: str = Depends(require_verified_email),
):
    try:
        row = get_conversation(conversation_id, user_id)
        return ConversationOut(**row)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to get conversation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def api_update_conversation(
    conversation_id: str,
    request: ConversationUpdate,
    user_id: str = Depends(require_verified_email),
):
    try:
        row = get_conversation(conversation_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    updates = request.model_dump(exclude_none=True)
    if not updates:
        return ConversationOut(**row)

    try:
        updated = update_conversation(conversation_id, user_id, updates)
        return ConversationOut(**updated)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to update conversation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{conversation_id}/rename", response_model=ConversationOut)
async def api_rename_conversation(
    conversation_id: str,
    request: RenameConversationRequest,
    user_id: str = Depends(require_verified_email),
):
    try:
        return rename_conversation(conversation_id, user_id, request.title)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to rename conversation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{conversation_id}/pin", response_model=ConversationOut)
async def api_pin_conversation(
    conversation_id: str,
    user_id: str = Depends(require_verified_email),
):
    try:
        return pin_conversation(conversation_id, user_id, True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to pin conversation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{conversation_id}/unpin", response_model=ConversationOut)
async def api_unpin_conversation(
    conversation_id: str,
    user_id: str = Depends(require_verified_email),
):
    try:
        return pin_conversation(conversation_id, user_id, False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to unpin conversation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{conversation_id}/archive", response_model=ConversationOut)
async def api_archive_conversation(
    conversation_id: str,
    user_id: str = Depends(require_verified_email),
):
    try:
        return archive_conversation(conversation_id, user_id, True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to archive conversation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{conversation_id}/unarchive", response_model=ConversationOut)
async def api_unarchive_conversation(
    conversation_id: str,
    user_id: str = Depends(require_verified_email),
):
    try:
        return archive_conversation(conversation_id, user_id, False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to unarchive conversation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{conversation_id}/folder", response_model=ConversationOut)
async def api_move_to_folder(
    conversation_id: str,
    request: FolderRequest,
    user_id: str = Depends(require_verified_email),
):
    try:
        return move_conversation_to_folder(conversation_id, user_id, request.folder)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to move conversation to folder")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{conversation_id}")
async def api_delete_conversation(
    conversation_id: str,
    user_id: str = Depends(require_verified_email),
):
    try:
        delete_conversation(conversation_id, user_id)
        return {"status": "ok", "message": "Conversation deleted"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to delete conversation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def api_get_messages(
    conversation_id: str,
    user_id: str = Depends(require_verified_email),
    limit: int = 100,
    offset: int = 0,
):
    try:
        return get_messages(conversation_id, user_id, limit=limit, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to get messages")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{conversation_id}/messages", response_model=MessageOut)
async def api_add_message(
    conversation_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(require_verified_email),
):
    try:
        return add_message(
            conversation_id,
            user_id,
            request.role,
            request.content,
            model_used=request.model_used,
            tokens_used=request.tokens_used,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to add message")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{conversation_id}/recent-messages")
async def api_get_recent_messages(
    conversation_id: str,
    user_id: str = Depends(require_verified_email),
    limit: int = 10,
):
    try:
        return get_recent_messages(conversation_id, user_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to get recent messages")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
