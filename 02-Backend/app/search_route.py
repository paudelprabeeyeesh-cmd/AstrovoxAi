"""Advanced Search API Routes.

Exposes endpoints for:
- Unified advanced search (hybrid, BM25, dense, web, images, videos, news, academic)
- Internal document search
- Video search
- Source verification
- Citation generation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field

from app.utils.auth.auth_utils import get_user_id_from_token
from app.search_unified import UnifiedSearchEngine, verify_source, video_search
from app.search_verifier import verify_sources_batch, get_verification_summary
from app.rag_search import RAGSearchEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["advanced-search"])

_unified = UnifiedSearchEngine()
_rag = RAGSearchEngine()


class AdvancedSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(10, ge=1, le=50)
    alpha: float = Field(0.5, ge=0.0, le=1.0)
    sources: Optional[List[str]] = Field(default_factory=lambda: ["hybrid", "web", "internal"])
    include_web: bool = True
    include_images: bool = False
    include_videos: bool = False
    include_news: bool = False
    include_academic: bool = False
    include_internal: bool = True
    rerank: bool = True
    generate_citations: bool = True
    verify_sources: bool = True
    query_embedding: Optional[List[float]] = None


class InternalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = "system"
    top_k: int = Field(10, ge=1, le=50)
    alpha: float = Field(0.5, ge=0.0, le=1.0)
    rerank: bool = True


class VideoSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(10, ge=1, le=50)


class VerificationRequest(BaseModel):
    results: List[Dict[str, Any]]


class CitationRequest(BaseModel):
    title: str = Field(..., min_length=1)
    authors: List[str] = Field(default_factory=list)
    year: str = ""
    source: str = ""
    url: str = ""
    style: str = "apa"
    page: Optional[int] = None
    chunk_id: Optional[str] = None


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field("system", min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    alpha: float = Field(0.5, ge=0.0, le=1.0)
    strategy: str = Field("hybrid", min_length=1, max_length=20)


@router.post("/advanced")
async def advanced_search(request: AdvancedSearchRequest, authorization: str = Header(None)):
    try:
        user_id = "system"
        if authorization:
            try:
                user_id = get_user_id_from_token(authorization) or "system"
            except Exception:
                user_id = "system"
        result = _unified.search(
            query=request.query,
            user_id=user_id,
            top_k=request.top_k,
            alpha=request.alpha,
            sources=request.sources,
            include_web=request.include_web,
            include_images=request.include_images,
            include_videos=request.include_videos,
            include_news=request.include_news,
            include_academic=request.include_academic,
            include_internal=request.include_internal,
            rerank=request.rerank,
            generate_citations=request.generate_citations,
            verify_sources=request.verify_sources,
            query_embedding=request.query_embedding,
        )
        return {"status": "OK", **result}
    except Exception as exc:
        logger.exception("Advanced search failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/internal")
async def internal_search(request: InternalSearchRequest, authorization: str = Header(None)):
    try:
        user_id = request.user_id
        if authorization:
            try:
                user_id = get_user_id_from_token(authorization) or user_id
            except Exception:
                pass
        result = _unified.search(
            query=request.query,
            user_id=user_id,
            top_k=request.top_k,
            alpha=request.alpha,
            sources=["internal"],
            include_internal=True,
            include_web=False,
            rerank=request.rerank,
            generate_citations=False,
            verify_sources=False,
        )
        return {"status": "OK", **result}
    except Exception as exc:
        logger.exception("Internal search failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/web")
async def web_search_endpoint(query: str, top_k: int = 10):
    try:
        result = _unified.search(
            query=query,
            top_k=top_k,
            sources=["web"],
            include_web=True,
            include_internal=False,
            rerank=False,
            generate_citations=True,
            verify_sources=True,
        )
        return {"status": "OK", **result}
    except Exception as exc:
        logger.exception("Web search failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/images")
async def image_search_endpoint(query: str, top_k: int = 10):
    try:
        result = _unified.search(
            query=query,
            top_k=top_k,
            sources=["images"],
            include_images=True,
            include_web=False,
            include_internal=False,
            rerank=False,
            generate_citations=False,
            verify_sources=False,
        )
        return {"status": "OK", **result}
    except Exception as exc:
        logger.exception("Image search failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/videos")
async def video_search_endpoint(request: VideoSearchRequest):
    try:
        results = video_search(request.query, request.top_k)
        verified = verify_sources_batch([
            {"url": r.get("url", ""), "source_type": "video", **r} for r in results
        ])
        return {
            "status": "OK",
            "query": request.query,
            "results": verified,
            "source": "video_search",
            "result_count": len(verified),
        }
    except Exception as exc:
        logger.exception("Video search failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/news")
async def news_search_endpoint(query: str, top_k: int = 10):
    try:
        result = _unified.search(
            query=query,
            top_k=top_k,
            sources=["news"],
            include_news=True,
            include_web=False,
            include_internal=False,
            rerank=False,
            generate_citations=True,
            verify_sources=True,
        )
        return {"status": "OK", **result}
    except Exception as exc:
        logger.exception("News search failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/academic")
async def academic_search_endpoint(query: str, top_k: int = 10):
    try:
        result = _unified.search(
            query=query,
            top_k=top_k,
            sources=["academic"],
            include_academic=True,
            include_web=False,
            include_internal=False,
            rerank=False,
            generate_citations=True,
            verify_sources=True,
        )
        return {"status": "OK", **result}
    except Exception as exc:
        logger.exception("Academic search failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/verify")
async def verify_sources_endpoint(request: VerificationRequest):
    try:
        verified = verify_sources_batch(request.results)
        summary = get_verification_summary(verified)
        return {"status": "OK", "results": verified, "summary": summary}
    except Exception as exc:
        logger.exception("Source verification failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/citations/generate")
async def generate_citation(request: CitationRequest):
    try:
        from app.search_knowledge import CitationEngine
        engine = CitationEngine()
        citation = engine.generate(
            document_title=request.title,
            authors=request.authors,
            year=request.year,
            source=request.source,
            url=request.url,
            style=request.style,
            page=request.page,
            chunk_id=request.chunk_id,
        )
        return {"status": "OK", "citation": citation.__dict__}
    except Exception as exc:
        logger.exception("Citation generation failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/rag/search")
async def rag_search(request: RAGSearchRequest, authorization: str = Header(None)):
    try:
        user_id = request.user_id
        if authorization:
            try:
                user_id = get_user_id_from_token(authorization) or user_id
            except Exception:
                pass
        result = _rag.search(
            query=request.query,
            user_id=user_id,
            top_k=request.top_k,
            alpha=request.alpha,
            strategy=request.strategy,
        )
        return {"status": "OK", **result}
    except Exception as exc:
        logger.exception("RAG search failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/health")
async def search_health():
    return {
        "status": "ok",
        "features": [
            "hybrid_search",
            "bm25",
            "dense_retrieval",
            "reranking",
            "web_search",
            "internal_document_search",
            "image_search",
            "video_search",
            "citation_generation",
            "source_verification",
        ],
    }
