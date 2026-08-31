from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

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
from .usage import DailyUsageTracker, UsageQuotaExceeded
from .providers import (
    ChatMessage,
    ProviderFactory,
    is_valid_model,
    get_model_info,
    get_provider_for_model,
)
from .metrics import track_ai_request

router = APIRouter(prefix="/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)
usage_tracker = DailyUsageTracker()


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = "gpt-4"


class SendMessageRequest(BaseModel):
    conversation_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=4000)
    model: Optional[str] = Field(default="gpt-4", min_length=1, max_length=64)


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str


class ModelsResponse(BaseModel):
    models: list[dict]


@router.post("/conversations")
async def create_new_conversation(
    request: CreateConversationRequest, authorization: str = Header(None)
):
    """Create a new conversation"""
    user_id = get_user_id_from_token(authorization)

    if request.model and not is_valid_model(request.model):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported model")

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
@limiter.limit("30/minute")
async def send_message(request: SendMessageRequest, authorization: str = Header(None)):
    """Send a message and get AI response (multi-provider)"""
    user_id = get_user_id_from_token(authorization)

    model = request.model or "gpt-4"

    # Validate model
    if not is_valid_model(model):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported model: {model}",
        )

    # Get provider for model
    provider_name = get_provider_for_model(model)
    provider = ProviderFactory.get(provider_name) if provider_name else None

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No provider available for model: {model}. Configure {provider_name.upper()}_API_KEY.",
        )

    if not provider.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider {provider_name} is not configured. Set the {provider_name.upper()}_API_KEY environment variable.",
        )

    try:
        normalized_message = request.message.strip()
        if not normalized_message:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message content cannot be empty",
            )
        if len(normalized_message) > 4000:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message content is too long",
            )

        try:
            await usage_tracker.record_success(user_id)
        except UsageQuotaExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
            ) from exc

        conversation = await get_conversation(request.conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        user_msg = await create_message(
            request.conversation_id, user_id, "user", normalized_message
        )

        messages = await get_recent_messages(request.conversation_id, limit=10)
        memory = await get_user_memory(user_id, limit=5)

        context_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]

        system_prompt = None
        if memory:
            system_prompt = "User context/memory:\n" + "\n".join(
                [m["content"] for m in memory[:3]]
            )

        model_info = get_model_info(model)
        actual_model = model_info.id if model_info else model

        try:
            response = await provider.chat(
                messages=context_messages,
                model=actual_model,
                temperature=0.7,
                max_tokens=2000,
                system_prompt=system_prompt,
            )
            track_ai_request(model=actual_model, status="success", tokens=response.tokens_used or 0)
        except Exception as e:
            track_ai_request(model=actual_model, status="error")
            sanitized = provider.sanitize_error(e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Provider {provider_name} error: {sanitized}",
            )

        ai_msg = await create_message(
            request.conversation_id,
            user_id,
            "assistant",
            response.content,
            model_used=model,
            tokens_used=response.tokens_used,
        )

        await update_conversation(request.conversation_id, last_message_at="now()")

        if "important" in response.content.lower() or "remember" in response.content.lower():
            await save_memory(
                user_id,
                f"User asked: {normalized_message}\nAI responded: {response.content[:200]}",
                importance=2,
            )

        return {
            "status": "OK",
            "user_message": user_msg,
            "ai_message": ai_msg,
            "tokens_used": response.tokens_used,
            "provider": provider_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.get("/models")
async def list_models():
    """List all supported models across all providers."""
    from .providers import list_models
    models = list_models()
    return {
        "status": "OK",
        "models": [
            {
                "id": m.id,
                "provider": m.provider,
                "display_name": m.display_name,
                "supports_streaming": m.supports_streaming,
                "description": m.description,
            }
            for m in models
        ],
    }


@router.post("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: int, title: str, authorization: str = Header(None)
):
    """Update conversation title"""
    user_id = get_user_id_from_token(authorization)

    try:
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
