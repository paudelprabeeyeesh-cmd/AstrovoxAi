import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..core.llm import LLMClient
from ...schemas import EmbeddingRequest, EmbeddingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["embeddings"])


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embedding(req: EmbeddingRequest, user_id: str = Depends(require_verified_email)):
    try:
        client = LLMClient()
        texts = req.texts if isinstance(req.texts, list) else [req.texts]
        embeddings = []
        for text in texts:
            embedding = client.embed_text(text, model=req.model or "text-embedding-3-small")
            embeddings.append(embedding)
        return EmbeddingResponse(
            embeddings=embeddings,
            model=req.model or "text-embedding-3-small",
            dimensions=len(embeddings[0]) if embeddings else 0,
        )
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/embeddings/models")
async def list_embedding_models(user_id: str = Depends(require_verified_email)):
    return [
        {"model_id": "text-embedding-3-small", "dimensions": 1536, "max_input": 8191},
        {"model_id": "text-embedding-3-large", "dimensions": 3072, "max_input": 8191},
    ]
