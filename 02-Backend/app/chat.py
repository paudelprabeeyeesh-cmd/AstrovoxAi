import asyncio
import json
import os
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from openai import OpenAI

from .auth_utils import get_user_id_from_token
from .database import (
    create_conversation,
    get_conversations,
    get_conversation,
    update_conversation,
    create_message,
    get_messages,
    get_recent_messages,
    get_user_memory,
    save_memory,
    delete_conversation,
)

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# Pydantic models
class CreateConversationRequest(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = "gpt-4"


class SendMessageRequest(BaseModel):
    conversation_id: int
    message: str = Field(min_length=1, max_length=40_000)
    model: str = Field(default="gpt-4", min_length=1, max_length=120)


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str


def _build_completion_messages(messages: list[dict[str, Any]], memory: list[dict[str, Any]]):
    """Build a bounded model context from persisted conversation state."""
    context_messages = [
        {"role": message["role"], "content": message["content"]}
        for message in messages
    ]
    if not memory:
        return context_messages

    memory_context = "User context/memory:\n" + "\n".join(
        memory_item["content"] for memory_item in memory[:3]
    )
    return [{"role": "system", "content": memory_context}, *context_messages]


async def _prepare_chat_request(request: SendMessageRequest, user_id: str):
    """Authorize, persist the prompt, and assemble context shared by chat transports."""
    conversation = await get_conversation(request.conversation_id, user_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    user_message = await create_message(
        request.conversation_id, user_id, "user", request.message
    )
    messages = await get_recent_messages(request.conversation_id, limit=10)
    memory = await get_user_memory(user_id, limit=5)
    return user_message, _build_completion_messages(messages, memory)


async def _persist_assistant_response(
    request: SendMessageRequest, user_id: str, content: str, tokens_used: Optional[int]
):
    """Persist a completed response and its lightweight memory signal."""
    assistant_message = await create_message(
        request.conversation_id,
        user_id,
        "assistant",
        content,
        model_used=request.model,
        tokens_used=tokens_used,
    )
    await update_conversation(request.conversation_id, last_message_at="now()")

    if "important" in content.lower() or "remember" in content.lower():
        await save_memory(
            user_id,
            f"User asked: {request.message}\nAI responded: {content[:200]}",
            importance=2,
        )
    return assistant_message


def _sse(event: str, payload: dict[str, Any]) -> str:
    """Encode an SSE event without allowing event-boundary injection."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _next_stream_chunk(stream):
    """Read one synchronous SDK chunk in a worker without leaking StopIteration."""
    try:
        return next(stream)
    except StopIteration:
        return None


@router.post("/conversations")
async def create_new_conversation(
    request: CreateConversationRequest, authorization: str = Header(None)
):
    """Create a new conversation"""
    user_id = get_user_id_from_token(authorization)

    try:
        conversation = await create_conversation(user_id, request.title, request.model)
        return {"status": "OK", "conversation": conversation}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}",
        )


@router.get("/conversations")
async def list_conversations(
    authorization: str = Header(None), limit: int = 50, offset: int = 0
):
    """List user's conversations"""
    user_id = get_user_id_from_token(authorization)

    try:
        conversations = await get_conversations(user_id, limit, offset)
        return {
            "status": "OK",
            "conversations": conversations,
            "count": len(conversations),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversations: {str(e)}",
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: int, authorization: str = Header(None)
):
    """Get conversation details"""
    user_id = get_user_id_from_token(authorization)

    try:
        conversation = await get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        return {"status": "OK", "conversation": conversation}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation: {str(e)}",
        )


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    authorization: str = Header(None),
    limit: int = 100,
    offset: int = 0,
):
    """Get messages from a conversation"""
    user_id = get_user_id_from_token(authorization)

    try:
        # Verify user owns this conversation
        conversation = await get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        messages = await get_messages(conversation_id, limit, offset)
        return {"status": "OK", "messages": messages, "count": len(messages)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch messages: {str(e)}",
        )


@router.post("/message")
async def send_message(request: SendMessageRequest, authorization: str = Header(None)):
    """Send a message and get AI response"""
    user_id = get_user_id_from_token(authorization)

    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI client not configured",
        )

    try:
        user_msg, completion_messages = await _prepare_chat_request(request, user_id)

        # Call OpenAI API
        response = client.chat.completions.create(
            model=request.model,
            messages=completion_messages,
            temperature=0.7,
            max_tokens=2000,
        )

        ai_response = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else None

        ai_msg = await _persist_assistant_response(
            request, user_id, ai_response, tokens_used
        )

        return {
            "status": "OK",
            "user_message": user_msg,
            "ai_message": ai_msg,
            "tokens_used": tokens_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.post("/stream")
async def stream_message(
    request: SendMessageRequest, authorization: str = Header(None)
):
    """Stream a persisted assistant response as Server-Sent Events.

    Event types are `message`, `token`, `done`, and `error`. The final assistant
    message is only persisted after the provider stream completes successfully.
    """
    user_id = get_user_id_from_token(authorization)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI client not configured",
        )

    user_message, completion_messages = await _prepare_chat_request(request, user_id)

    async def event_stream() -> AsyncIterator[str]:
        content_parts: list[str] = []
        tokens_used: Optional[int] = None
        try:
            provider_stream = await asyncio.to_thread(
                client.chat.completions.create,
                model=request.model,
                messages=completion_messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True,
                stream_options={"include_usage": True},
            )
            yield _sse("message", {"message": user_message})

            while True:
                chunk = await asyncio.to_thread(_next_stream_chunk, provider_stream)
                if chunk is None:
                    break

                if getattr(chunk, "usage", None):
                    tokens_used = chunk.usage.total_tokens
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                token = getattr(choices[0].delta, "content", None)
                if token:
                    content_parts.append(token)
                    yield _sse("token", {"content": token})

            content = "".join(content_parts)
            assistant_message = await _persist_assistant_response(
                request, user_id, content, tokens_used
            )
            yield _sse(
                "done",
                {"message": assistant_message, "tokens_used": tokens_used},
            )
        except Exception:
            yield _sse(
                "error",
                {"detail": "The response stream ended unexpectedly. Please try again."},
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: int, title: str, authorization: str = Header(None)
):
    """Update conversation title"""
    user_id = get_user_id_from_token(authorization)

    try:
        # Verify user owns this conversation
        conversation = await get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        updated = await update_conversation(conversation_id, title=title)
        return {"status": "OK", "conversation": updated}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}",
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation_route(
    conversation_id: int, authorization: str = Header(None)
):
    """Delete a conversation"""
    user_id = get_user_id_from_token(authorization)

    try:
        # Verify user owns this conversation
        conversation = await get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        await delete_conversation(conversation_id)

        return {"status": "OK", "message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}",
        )
