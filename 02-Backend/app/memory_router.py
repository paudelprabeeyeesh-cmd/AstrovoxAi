"""HTTP API for user-managed memories.

This module is deliberately named differently from the ``app.memory`` package so
the API router and the layered memory domain can coexist without import shadowing.
"""

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status
from openai import OpenAI
from pydantic import BaseModel, Field

from .auth_utils import get_user_id_from_token
from .database import get_recent_messages, get_user_memory, save_memory

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryEntry(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)
    importance: int = Field(default=1, ge=1, le=5)


async def _get_owned_messages(conversation_id: int, user_id: str):
    """Return messages only after confirming the requester owns the conversation."""
    from .database import get_conversation

    conversation = await get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return await get_recent_messages(conversation_id, limit=20)


@router.post("/save")
async def save_memory_entry(entry: MemoryEntry, authorization: str = Header(None)):
    """Save a user-authored memory entry."""
    user_id = get_user_id_from_token(authorization)
    memory = await save_memory(user_id, entry.content, entry.importance)
    if not memory:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save memory")
    return {"status": "OK", "memory": memory}


@router.get("/")
async def get_memory(authorization: str = Header(None), limit: int = 50):
    """List the requester's memories."""
    user_id = get_user_id_from_token(authorization)
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit must be 1-100")
    memory = await get_user_memory(user_id, limit)
    return {"status": "OK", "memory": memory, "count": len(memory)}


@router.post("/extract-from-conversation")
async def extract_memory_from_conversation(
    conversation_id: int, authorization: str = Header(None)
):
    """Save bounded heuristic memories from an owned conversation."""
    user_id = get_user_id_from_token(authorization)
    messages = await _get_owned_messages(conversation_id, user_id)
    keywords = {"important", "remember", "note", "key", "critical", "must", "should"}
    extracted = []

    for message in messages:
        content = message["content"]
        if message["role"] == "assistant" and any(word in content.lower() for word in keywords):
            memory = await save_memory(user_id, f"From conversation: {content[:200]}", importance=2)
            if memory:
                extracted.append(memory)

    return {"status": "OK", "extracted": extracted, "count": len(extracted)}


@router.post("/context")
async def get_memory_context(authorization: str = Header(None), limit: int = 5):
    """Return formatted memory context for a user-visible inspection flow."""
    user_id = get_user_id_from_token(authorization)
    if not 1 <= limit <= 20:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit must be 1-20")
    memory = await get_user_memory(user_id, limit)
    context = "\n".join(["User Context/Memory:", *[f"- {entry['content']}" for entry in memory]]) if memory else ""
    return {"status": "OK", "context": context, "memory_count": len(memory)}


@router.post("/auto-extract")
async def auto_extract_memory(conversation_id: int, authorization: str = Header(None)):
    """Extract a concise memory from an owned conversation using the configured model."""
    user_id = get_user_id_from_token(authorization)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider not configured")

    messages = await _get_owned_messages(conversation_id, user_id)
    if not messages:
        return {"status": "OK", "message": "No messages to extract from", "extracted": []}

    conversation_text = "\n".join(f"{message['role'].upper()}: {message['content']}" for message in messages)
    try:
        response = OpenAI(api_key=api_key).chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "Extract facts and preferences worth remembering. Return a concise bullet list.",
                },
                {"role": "user", "content": conversation_text},
            ],
            temperature=0.5,
            max_tokens=500,
        )
        extracted_text = response.choices[0].message.content or ""
        memory = await save_memory(user_id, extracted_text, importance=3)
        return {"status": "OK", "extracted": extracted_text, "memory": memory}
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Memory extraction failed") from error
