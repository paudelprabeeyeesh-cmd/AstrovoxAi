"""Embeddings API routes — generate vector embeddings for text."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from .embeddings import embedding_service

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=100)
    model: Optional[str] = None


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model: str
    count: int


class EmbedOneRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = None


@router.post("/", response_model=EmbedResponse)
async def generate_embeddings(request: EmbedRequest):
    """Generate embeddings for a list of texts."""
    if not embedding_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service not configured. Set GEMINI_API_KEY.",
        )

    try:
        results = await embedding_service.embed_with_retry(
            texts=request.texts,
            model=request.model,
        )
        return {
            "embeddings": [r.vector for r in results],
            "model": request.model or embedding_service.model,
            "count": len(results),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {str(e)}",
        )


@router.post("/one", response_model=EmbedResponse)
async def generate_one_embedding(request: EmbedOneRequest):
    """Generate embedding for a single text."""
    if not embedding_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service not configured. Set GEMINI_API_KEY.",
        )

    try:
        result = await embedding_service.embed_one(
            text=request.text,
            model=request.model,
        )
        return {
            "embeddings": [result.vector],
            "model": request.model or embedding_service.model,
            "count": 1,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {str(e)}",
        )


@router.get("/status")
async def embedding_status():
    """Check embedding service status."""
    return {
        "configured": embedding_service.is_configured,
        "model": embedding_service.model,
    }
