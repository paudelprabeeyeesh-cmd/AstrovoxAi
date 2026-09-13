"""Embedding API endpoints."""

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from ..auth_utils import get_user_id_from_token
from .service import EmbeddingService

router = APIRouter(prefix="/api/embedding", tags=["embedding"])


class EmbedRequest(BaseModel):
    text: str
    model: Optional[str] = None
    provider: Optional[str] = "openai"


class EmbedBatchRequest(BaseModel):
    texts: list[str]
    model: Optional[str] = None
    provider: Optional[str] = "openai"


class SimilarityRequest(BaseModel):
    text_a: str
    text_b: str
    model: Optional[str] = None
    provider: Optional[str] = "openai"


class EmbeddingResponse(BaseModel):
    vector: list[float]
    model: str
    provider: str
    dimensions: int


class SimilarityResponse(BaseModel):
    similarity: float
    model: str
    provider: str


@router.post("/", response_model=EmbeddingResponse)
async def create_embedding(request: EmbedRequest, authorization: str = Header(None)):
    """Generate an embedding for a single text."""
    get_user_id_from_token(authorization)

    service = EmbeddingService(
        provider_name=request.provider or "openai",
        model=request.model,
    )

    try:
        result = await service.embed_text(request.text)
        return EmbeddingResponse(
            vector=result.vector,
            model=result.model,
            provider=result.provider,
            dimensions=result.dimensions,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding failed: {str(e)}",
        )


@router.post("/batch")
async def create_batch_embeddings(request: EmbedBatchRequest, authorization: str = Header(None)):
    """Generate embeddings for multiple texts."""
    get_user_id_from_token(authorization)

    if len(request.texts) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Batch size exceeds maximum of 100",
        )

    service = EmbeddingService(
        provider_name=request.provider or "openai",
        model=request.model,
    )

    try:
        result = await service.embed_batch(request.texts)
        return {
            "embeddings": [
                {"vector": e.vector, "dimensions": e.dimensions}
                for e in result.embeddings
            ],
            "model": result.model,
            "provider": result.provider,
            "total_tokens": result.total_tokens,
            "batch_size": result.batch_size,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Batch embedding failed: {str(e)}",
        )


@router.post("/similarity", response_model=SimilarityResponse)
async def calculate_similarity(request: SimilarityRequest, authorization: str = Header(None)):
    """Calculate semantic similarity between two texts."""
    get_user_id_from_token(authorization)

    service = EmbeddingService(
        provider_name=request.provider or "openai",
        model=request.model,
    )

    try:
        sim = await service.similarity(request.text_a, request.text_b)
        return SimilarityResponse(
            similarity=sim,
            model=service.model or service.provider.default_model if service.provider else "unknown",
            provider=service.provider_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Similarity calculation failed: {str(e)}",
        )


@router.get("/providers")
async def list_embedding_providers(authorization: str = Header(None)):
    """List available embedding providers."""
    get_user_id_from_token(authorization)

    from .embedding.providers import EmbeddingProviderFactory
    configured = EmbeddingProviderFactory.list_configured()

    return {
        "providers": [
            {
                "name": name,
                "configured": name in configured,
            }
            for name in ["openai", "ollama"]
        ]
    }


@router.get("/status")
async def embedding_status(authorization: str = Header(None)):
    """Check embedding service status."""
    get_user_id_from_token(authorization)

    from .providers import EmbeddingProviderFactory
    configured = EmbeddingProviderFactory.list_configured()

    return {
        "configured": len(configured) > 0,
        "providers": configured,
        "default_model": "text-embedding-3-small",
    }
