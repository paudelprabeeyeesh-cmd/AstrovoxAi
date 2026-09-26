"""REST API routes for the platform."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field

from app.utils.auth.auth_utils import get_user_id_from_token
from app.api.custom_tools import tool_registry
from app.api.webhooks import webhook_manager
from app.safety.input_moderation import input_moderator
from app.safety.output_moderation import output_moderator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["rest-api"])


class ChatRequest(BaseModel):
    model: str = "gpt-4"
    messages: list[dict] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 1024


class ChatResponse(BaseModel):
    id: str
    model: str
    choices: list[dict]
    usage: dict


class CompletionRequest(BaseModel):
    model: str = "gpt-4"
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 1024


class CompletionResponse(BaseModel):
    id: str
    text: str
    model: str
    usage: dict


class EmbeddingRequest(BaseModel):
    model: str = "text-embedding-3-small"
    input: str


class EmbeddingResponse(BaseModel):
    model: str
    embeddings: list[list[float]]


@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    moderation = input_moderator.moderate(" ".join(m.get("content", "") for m in request.messages))
    if not moderation.safe:
        raise HTTPException(status_code=400, detail={"moderation": moderation.__dict__})
    # Placeholder inference call
    response_text = "[simulated response]"
    output_mod = output_moderator.moderate(response_text)
    if not output_mod.safe:
        response_text = output_mod.sanitized_text or "[filtered]"
    return ChatResponse(
        id="chatcmpl-123",
        model=request.model,
        choices=[{"index": 0, "message": {"role": "assistant", "content": response_text}}],
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    )


@router.post("/completions", response_model=CompletionResponse)
async def completions(request: CompletionRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    moderation = input_moderator.moderate(request.prompt)
    if not moderation.safe:
        raise HTTPException(status_code=400, detail={"moderation": moderation.__dict__})
    return CompletionResponse(
        id="cmpl-123",
        text="[simulated completion]",
        model=request.model,
        usage={"prompt_tokens": 5, "completion_tokens": 15, "total_tokens": 20},
    )


@router.post("/embeddings", response_model=EmbeddingResponse)
async def embeddings(request: EmbeddingRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    return EmbeddingResponse(model=request.model, embeddings=[[0.1] * 1536])


@router.get("/models")
async def list_models(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4", "object": "model", "owned_by": "astrovox"},
            {"id": "gpt-4o-mini", "object": "model", "owned_by": "astrovox"},
        ],
    }


@router.get("/usage")
async def usage(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    return {"user_id": user_id, "requests_used": 42, "requests_limit": 1000}
