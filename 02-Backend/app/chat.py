from fastapi import APIRouter, HTTPException, status, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from slowapi import Limiter
from slowapi.util import get_remote_address
import time
import uuid
import logging

from .auth_utils import get_user_id_from_token
from .database import (
    create_conversation,
    get_conversations,
    get_conversation,
    update_conversation,
    create_message,
    get_messages,
    get_recent_messages,
    delete_conversation,
)
from .memory import MemoryManager, MemoryConsolidationService, memory_service
from .rag.retriever import RAGRetriever, RetrievalResult
from .usage import DailyUsageTracker, UsageQuotaExceeded
from .providers import (
    ChatMessage,
    ProviderFactory,
    is_valid_model,
    get_model_info,
    get_provider_for_model,
)
from .metrics import track_ai_request, track_ai_duration, track_request
from .sse import (
    format_sse,
    generate_event_id,
    KeepAliveGenerator,
    StreamFallbackChain,
    StreamState,
)

router = APIRouter(prefix="/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)
usage_tracker = DailyUsageTracker()
memory_manager = MemoryManager()
consolidation_service = MemoryConsolidationService()
logger = logging.getLogger(__name__)

PROVIDER_FALLBACK_ORDER = ["openai", "anthropic", "gemini", "ollama"]
STREAM_KEEPALIVE_INTERVAL = 15
MAX_STREAM_FALLBACKS = 2
STREAM_RETRY_AFTER_MS = 5000


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = "gpt-4"


class SendMessageRequest(BaseModel):
    conversation_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4000)
    model: Optional[str] = Field(default="gpt-4", min_length=1, max_length=64)
    stream: Optional[bool] = False
    last_event_id: Optional[str] = Field(default=None, alias="lastEventId")


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    model: str
    created_at: str
    updated_at: str


class MessagesResponse(BaseModel):
    messages: List[MessageResponse]
    count: int


class ModelsResponse(BaseModel):
    models: list[dict]


class StreamError(BaseModel):
    message: str
    detail: Optional[str] = None
    retry_after_ms: Optional[int] = None
    code: Optional[str] = None


class StreamMetadata(BaseModel):
    conversation_id: str
    model: str
    provider: str
    event_id: str
    resumed: bool = False


def _get_fallback_providers(primary_name: str, limit: int = MAX_STREAM_FALLBACKS) -> list:
    providers = []
    for name in PROVIDER_FALLBACK_ORDER:
        if name == primary_name:
            continue
        p = ProviderFactory.get(name)
        if p and p.is_configured and p.supports_streaming:
            providers.append(p)
        if len(providers) >= limit:
            break
    return providers


def _get_rag_context(user_id: str, query: str, top_k: int = 3) -> str:
    try:
        retriever = RAGRetriever()
        import asyncio
        results = asyncio.run(retriever.retrieve(query=query, top_k=top_k))
        if not results:
            return ""
        lines = ["Relevant Document Context:"]
        for r in results:
            lines.append(f"- [{r.source}] {r.content[:300]}")
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("RAG context retrieval failed: %s", exc)
        return ""


def _trigger_memory_consolidation(user_id: str):
    try:
        consolidation_service.consolidate_user(user_id=user_id)
    except Exception as exc:
        logger.warning("Memory consolidation failed: %s", exc)


def _resolve_stream_provider(model: str, provider_name: str):
    provider = ProviderFactory.get(provider_name) if provider_name else None
    if not provider or not provider.is_configured:
        return None, None, None
    model_info = get_model_info(model)
    actual_model = model_info.id if model_info else model
    if not provider.validate_model(actual_model):
        for fb_name in PROVIDER_FALLBACK_ORDER:
            if fb_name == provider_name:
                continue
            fb = ProviderFactory.get(fb_name)
            if fb and fb.is_configured and fb.supports_streaming:
                return fb, fb_name, actual_model
        return None, None, None
    return provider, provider_name, actual_model


def _parse_last_event_id(last_event_id: Optional[str]) -> bool:
    return bool(last_event_id and last_event_id.strip())


async def _stream_with_fallback(
    provider,
    provider_name,
    actual_model,
    context_messages,
    system_prompt,
    fallback_chain,
    event_id,
    stream_state: StreamState,
):
    async def _emit_chunks(prov, prov_name, model_id):
        nonlocal stream_state
        stream = prov.stream_with_retry(
            messages=context_messages,
            model=model_id,
            temperature=0.7,
            max_tokens=2000,
            system_prompt=system_prompt,
        )
        async for chunk in stream:
            stream_state.tokens_yielded += len(chunk.split())
            yield format_sse("token", {"content": chunk}, event_id=event_id)
        yield format_sse("done", {
            "provider": prov_name,
            "model": model_id,
            "content": "",
            "tokens_used": stream_state.tokens_yielded,
            "finish_reason": "stop",
            "fallback": stream_state.fallback_count > 0,
        }, event_id=event_id)

    try:
        async for sse in _emit_chunks(provider, provider_name, actual_model):
            yield sse
        return
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        sanitized = provider.sanitize_error(exc)
        next_provider = fallback_chain.next_provider(reason=sanitized)
        if next_provider:
            stream_state.fallback_count = fallback_chain.fallback_count
            fb_model = actual_model
            if not next_provider.validate_model(fb_model):
                for candidate_name in PROVIDER_FALLBACK_ORDER:
                    if candidate_name in (provider_name, getattr(next_provider, 'name', '')):
                        continue
                    candidate = ProviderFactory.get(candidate_name)
                    if candidate and candidate.is_configured and candidate.supports_streaming:
                        next_provider = candidate
                        break
            yield format_sse("fallback", {
                "from_provider": provider_name,
                "to_provider": next_provider.name,
                "reason": sanitized,
                "retry_after_ms": 1000,
            }, event_id=event_id, retry=1000)
            try:
                async for sse in _emit_chunks(next_provider, next_provider.name, fb_model):
                    yield sse
                return
            except asyncio.CancelledError:
                raise
            except Exception as fb_exc:  # noqa: BLE001
                sanitized = next_provider.sanitize_error(fb_exc)
                yield format_sse("error", {
                    "message": "All providers failed",
                    "detail": sanitized,
                    "retry_after_ms": STREAM_RETRY_AFTER_MS,
                    "code": "PROVIDERS_EXHAUSTED",
                }, event_id=event_id, retry=STREAM_RETRY_AFTER_MS)
                stream_state.error = sanitized
                return
        else:
            yield format_sse("error", {
                "message": "Provider error",
                "detail": sanitized,
                "retry_after_ms": STREAM_RETRY_AFTER_MS,
                "code": "PROVIDER_ERROR",
            }, event_id=event_id, retry=STREAM_RETRY_AFTER_MS)
            stream_state.error = sanitized
            return


@router.post("/stream")
@limiter.limit("30/minute")
async def stream_chat(request: SendMessageRequest, authorization: str = Header(None), last_event_id: Optional[str] = Header(None, convert_underscores=False)):
    user_id = get_user_id_from_token(authorization)
    model = request.model or "gpt-4"

    if not is_valid_model(model):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported model: {model}",
        )

    provider_name = get_provider_for_model(model)
    provider, resolved_provider_name, actual_model = _resolve_stream_provider(model, provider_name)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No streaming-capable provider available for model: {model}",
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

    await create_message(request.conversation_id, user_id, "user", normalized_message)
    messages = await get_recent_messages(request.conversation_id, limit=10)
    memory = await get_user_memory(user_id, limit=5)
    context_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]
    system_prompt = None
    if memory:
        system_prompt = "User context/memory:\n" + "\n".join([m["content"] for m in memory[:3]])
    rag_context = _get_rag_context(user_id, normalized_message)
    if rag_context:
        system_prompt = (system_prompt or "") + "\n\n" + rag_context

    event_id = generate_event_id()
    resumed = _parse_last_event_id(last_event_id or request.last_event_id)
    fallback_providers = _get_fallback_providers(resolved_provider_name)
    fallback_chain = StreamFallbackChain(provider, fallback_providers, max_fallbacks=MAX_STREAM_FALLBACKS)
    stream_state = StreamState(
        event_id=event_id,
        provider=resolved_provider_name,
        model=actual_model,
    )

    async def event_generator():
        start_time = time.time()
        try:
            yield format_sse("metadata", StreamMetadata(
                conversation_id=request.conversation_id,
                model=actual_model,
                provider=resolved_provider_name,
                event_id=event_id,
                resumed=resumed,
            ).dict(), event_id=event_id)

            async for sse in _stream_with_fallback(
                provider, resolved_provider_name, actual_model,
                context_messages, system_prompt, fallback_chain, event_id,
                stream_state,
            ):
                yield sse
        except asyncio.CancelledError:
            logger.info("Stream cancelled by client: %s", event_id)
            yield format_sse("error", {
                "message": "Stream cancelled by client",
                "detail": "Client disconnected",
                "code": "CLIENT_CANCELLED",
            }, event_id=event_id)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Stream error: %s", exc)
            sanitized = provider.sanitize_error(exc) if provider else str(exc)
            yield format_sse("error", {
                "message": "Stream failed",
                "detail": sanitized,
                "retry_after_ms": STREAM_RETRY_AFTER_MS,
                "code": "STREAM_ERROR",
            }, event_id=event_id, retry=STREAM_RETRY_AFTER_MS)
            stream_state.error = sanitized
        finally:
            duration = time.time() - start_time
            track_ai_duration(model=actual_model, duration=duration)
            track_ai_request(model=actual_model, status="error" if stream_state.error else "success")
            _trigger_memory_consolidation(user_id)

    keepalive = KeepAliveGenerator(interval_seconds=STREAM_KEEPALIVE_INTERVAL, event_id=event_id)
    return StreamingResponse(
        keepalive.generate(event_generator()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "X-Event-ID": event_id,
        },
    )


@router.post("/message")
@limiter.limit("30/minute")
async def send_message(request: SendMessageRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)

    model = request.model or "gpt-4"

    if not is_valid_model(model):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported model: {model}",
        )

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
            request.conversation_id,
            user_id,
            "user",
            normalized_message
        )

        messages = await get_recent_messages(request.conversation_id, limit=10)
        memory = await get_user_memory(user_id, limit=5)

        context_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]

        system_prompt = None
        if memory:
            system_prompt = "User context/memory:\n" + "\n".join(
                [m["content"] for m in memory[:3]]
            )
        rag_context = _get_rag_context(user_id, normalized_message)
        if rag_context:
            system_prompt = (system_prompt or "") + "\n\n" + rag_context

        model_info = get_model_info(model)
        actual_model = model_info.id if model_info else model

        if request.stream and provider.supports_streaming:
            event_id = generate_event_id()
            stream_state = StreamState(
                event_id=event_id,
                provider=provider_name,
                model=actual_model,
            )

            async def stream_generator():
                start_time = time.time()
                full_content = ""
                try:
                    yield format_sse("metadata", StreamMetadata(
                        conversation_id=request.conversation_id,
                        model=actual_model,
                        provider=provider_name,
                        event_id=event_id,
                        resumed=False,
                    ).dict(), event_id=event_id)

                    async for chunk in provider.stream(
                        messages=context_messages,
                        model=actual_model,
                        temperature=0.7,
                        max_tokens=2000,
                        system_prompt=system_prompt,
                    ):
                        full_content += chunk
                        stream_state.tokens_yielded += len(chunk.split())
                        yield format_sse("token", {"content": chunk}, event_id=event_id)

                    yield format_sse("done", {
                        "provider": provider_name,
                        "model": actual_model,
                        "content": full_content,
                        "tokens_used": stream_state.tokens_yielded,
                        "finish_reason": "stop",
                        "fallback": False,
                    }, event_id=event_id)

                    ai_msg = await create_message(
                        request.conversation_id,
                        user_id,
                        "assistant",
                        full_content,
                        model_used=model,
                    )
                    await update_conversation(request.conversation_id, last_message_at="now()")
                    track_ai_request(model=actual_model, status="success")
                except asyncio.CancelledError:
                    logger.info("Stream cancelled by client: %s", event_id)
                    yield format_sse("error", {
                        "message": "Stream cancelled by client",
                        "detail": "Client disconnected",
                        "code": "CLIENT_CANCELLED",
                    }, event_id=event_id)
                    raise
                except Exception as e:  # noqa: BLE001
                    track_ai_request(model=actual_model, status="error")
                    sanitized = provider.sanitize_error(e)
                    yield format_sse("error", {
                        "message": "Stream failed",
                        "detail": sanitized,
                        "retry_after_ms": STREAM_RETRY_AFTER_MS,
                        "code": "STREAM_ERROR",
                    }, event_id=event_id, retry=STREAM_RETRY_AFTER_MS)
                    stream_state.error = sanitized
                finally:
                    duration = time.time() - start_time
                    track_ai_duration(model=actual_model, duration=duration)
                    _trigger_memory_consolidation(user_id)

            keepalive = KeepAliveGenerator(interval_seconds=STREAM_KEEPALIVE_INTERVAL, event_id=event_id)
            return StreamingResponse(
                keepalive.generate(stream_generator()),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive",
                    "X-Event-ID": event_id,
                },
            )

        try:
            response = await provider.chat_with_retry(
                messages=context_messages,
                model=actual_model,
                temperature=0.7,
                max_tokens=2000,
                system_prompt=system_prompt,
            )
            track_ai_request(model=actual_model, status="success", tokens=response.tokens_used or 0)
        except Exception as e:  # noqa: BLE001
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

        _trigger_memory_consolidation(user_id)

        return {
            "status": "OK",
            "user_message": user_msg,
            "ai_message": ai_msg,
            "tokens_used": response.tokens_used,
            "provider": provider_name,
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.get("/models")
async def list_models():
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


@router.post("/conversations")
async def create_conversation_route(
    request: CreateConversationRequest,
    authorization: str = Header(None),
):
    user_id = get_user_id_from_token(authorization)
    conversation = await create_conversation(
        user_id=user_id,
        title=request.title,
        model=request.model,
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation",
        )
    return {"status": "OK", "conversation": conversation}


@router.get("/conversations")
@limiter.limit("60/minute")
async def list_conversations(request: Request, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    conversations = await get_conversations(user_id)
    return {"status": "OK", "conversations": conversations, "count": len(conversations)}


@router.get("/conversations/{conversation_id}/messages")
@limiter.limit("60/minute")
async def get_conversation_messages(
    request: Request,
    conversation_id: str,
    authorization: str = Header(None),
    limit: int = 100,
    offset: int = 0,
):
    user_id = get_user_id_from_token(authorization)
    conversation = await get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    messages = await get_messages(conversation_id, limit=limit, offset=offset)
    return {
        "status": "OK",
        "messages": messages,
        "count": len(messages),
    }


@router.post("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str, title: str, authorization: str = Header(None)
):
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
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}",
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation_route(
    conversation_id: str, authorization: str = Header(None)
):
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
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}",
        )
