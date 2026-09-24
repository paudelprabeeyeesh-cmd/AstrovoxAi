"""
Extended RAG API routes.

Endpoints:
- POST /rag/ingest/markdown - Ingest markdown file
- POST /rag/ingest/html - Ingest HTML file
- POST /rag/ingest/csv - Ingest CSV file
- POST /rag/ingest/ocr - Ingest image/PDF with OCR
- POST /rag/ingest/audio - Ingest audio transcription
- POST /rag/ingest/video - Ingest video captions
- GET /rag/knowledge-base - List knowledge base documents
- POST /rag/knowledge-base - Add knowledge base document
- DELETE /rag/knowledge-base/{doc_id} - Delete knowledge base document
- GET /rag/incremental-index/stats - Get incremental index stats
- POST /rag/semantic-retrieval - Semantic retrieval
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field

from ..auth import require_verified_email, get_current_user
from app.parsers.document_parsers import DocumentParsers
from app.knowledge.knowledge_base import KnowledgeBase
from app.knowledge.incremental_indexing import IncrementalIndex
from app.knowledge.semantic_retrieval import SemanticRetriever
from app.multimodal.audio_video import AudioExtractor, VideoExtractor
from app.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag-extended"])

_knowledge_bases: Dict[str, KnowledgeBase] = {}
_incremental_indexes: Dict[str, IncrementalIndex] = {}
_semantic_retrievers: Dict[str, SemanticRetriever] = {}
_rag_pipelines: Dict[str, RAGPipeline] = {}


def _get_kb(user_id: str) -> KnowledgeBase:
    if user_id not in _knowledge_bases:
        _knowledge_bases[user_id] = KnowledgeBase()
    return _knowledge_bases[user_id]


def _get_index(user_id: str) -> IncrementalIndex:
    if user_id not in _incremental_indexes:
        _incremental_indexes[user_id] = IncrementalIndex()
    return _incremental_indexes[user_id]


def _get_retriever(user_id: str) -> SemanticRetriever:
    if user_id not in _semantic_retrievers:
        _semantic_retrievers[user_id] = SemanticRetriever()
    return _semantic_retrievers[user_id]


def _get_pipeline(user_id: str) -> RAGPipeline:
    if user_id not in _rag_pipelines:
        _rag_pipelines[user_id] = RAGPipeline(user_id=user_id)
    return _rag_pipelines[user_id]


class IngestMarkdownRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)
    filename: str = Field("document.md", max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestHtmlRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)
    filename: str = Field("document.html", max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestCsvRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)
    filename: str = Field("document.csv", max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestOcrRequest(BaseModel):
    file_path: str = Field(..., max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticRetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=50)


class KnowledgeBaseDocumentCreateRequest(BaseModel):
    title: str = Field(..., max_length=500)
    content: str = Field(..., max_length=100000)
    doc_type: str = Field("text", max_length=50)
    metadata: dict[str, Any] | None = None


class AudioTranscriptionRequest(BaseModel):
    file_path: str = Field(..., max_length=1000)
    model: str = Field("base", max_length=50)


class VideoCaptionRequest(BaseModel):
    file_path: str = Field(..., max_length=1000)


@router.post("/ingest/markdown")
async def ingest_markdown(request: IngestMarkdownRequest, user_id: str = Depends(require_verified_email)):
    try:
        pipeline = _get_pipeline(user_id)
        result = await pipeline.ingest_text(
            text=request.text,
            filename=request.filename,
            source_type="markdown",
            metadata=request.metadata,
        )
        return {
            "document_id": result.document_id,
            "filename": result.filename,
            "source_type": result.source_type,
            "chunks_created": result.chunks_created,
            "total_characters": result.total_characters,
            "created_at": result.created_at,
        }
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/ingest/html")
async def ingest_html(request: IngestHtmlRequest, user_id: str = Depends(require_verified_email)):
    try:
        pipeline = _get_pipeline(user_id)
        result = await pipeline.ingest_text(
            text=request.text,
            filename=request.filename,
            source_type="html",
            metadata=request.metadata,
        )
        return {
            "document_id": result.document_id,
            "filename": result.filename,
            "source_type": result.source_type,
            "chunks_created": result.chunks_created,
            "total_characters": result.total_characters,
            "created_at": result.created_at,
        }
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/ingest/csv")
async def ingest_csv(request: IngestCsvRequest, user_id: str = Depends(require_verified_email)):
    try:
        pipeline = _get_pipeline(user_id)
        result = await pipeline.ingest_text(
            text=request.text,
            filename=request.filename,
            source_type="csv",
            metadata=request.metadata,
        )
        return {
            "document_id": result.document_id,
            "filename": result.filename,
            "source_type": result.source_type,
            "chunks_created": result.chunks_created,
            "total_characters": result.total_characters,
            "created_at": result.created_at,
        }
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/ingest/ocr")
async def ingest_ocr(request: IngestOcrRequest, user_id: str = Depends(require_verified_email)):
    try:
        text = DocumentParsers.parse_pdf(request.file_path, ocr=True)
        if not text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No text extracted from file")
        pipeline = _get_pipeline(user_id)
        result = await pipeline.ingest_text(
            text=text,
            filename=os.path.basename(request.file_path),
            source_type="ocr",
            metadata=request.metadata,
        )
        return {
            "document_id": result.document_id,
            "filename": result.filename,
            "source_type": "ocr",
            "chunks_created": result.chunks_created,
            "total_characters": result.total_characters,
            "created_at": result.created_at,
        }
    except HTTPException:
        raise
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/ingest/audio")
async def ingest_audio(request: AudioTranscriptionRequest, user_id: str = Depends(require_verified_email)):
    try:
        text = AudioExtractor.transcribe(request.file_path, model=request.model)
        if not text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No transcription generated")
        pipeline = _get_pipeline(user_id)
        result = await pipeline.ingest_text(
            text=text,
            filename=os.path.basename(request.file_path),
            source_type="audio_transcript",
        )
        return {
            "document_id": result.document_id,
            "filename": result.filename,
            "source_type": "audio_transcript",
            "chunks_created": result.chunks_created,
            "total_characters": result.total_characters,
            "created_at": result.created_at,
        }
    except HTTPException:
        raise
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/ingest/video")
async def ingest_video(request: VideoCaptionRequest, user_id: str = Depends(require_verified_email)):
    try:
        captions = VideoExtractor.extract_captions(request.file_path)
        if not captions.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No captions extracted")
        pipeline = _get_pipeline(user_id)
        result = await pipeline.ingest_text(
            text=captions,
            filename=os.path.basename(request.file_path),
            source_type="video_captions",
        )
        return {
            "document_id": result.document_id,
            "filename": result.filename,
            "source_type": "video_captions",
            "chunks_created": result.chunks_created,
            "total_characters": result.total_characters,
            "created_at": result.created_at,
        }
    except HTTPException:
        raise
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.get("/knowledge-base")
async def list_knowledge_base(user_id: str = Depends(get_current_user)):
    try:
        kb = _get_kb(user_id)
        docs = kb.list_documents(user_id=user_id)
        return {"documents": docs}
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/knowledge-base")
async def create_knowledge_base_document(request: KnowledgeBaseDocumentCreateRequest, user_id: str = Depends(require_verified_email)):
    try:
        kb = _get_kb(user_id)
        doc_id = kb.add_document(
            user_id=user_id,
            title=request.title,
            content=request.content,
            doc_type=request.doc_type,
            metadata=request.metadata,
        )
        return {"doc_id": doc_id, "status": "created"}
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.delete("/knowledge-base/{doc_id}")
async def delete_knowledge_base_document(doc_id: str, user_id: str = Depends(require_verified_email)):
    try:
        kb = _get_kb(user_id)
        deleted = kb.delete_document(doc_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.get("/incremental-index/stats")
async def get_incremental_index_stats(user_id: str = Depends(get_current_user)):
    try:
        idx = _get_index(user_id)
        stats = idx.get_stats()
        return stats
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None


@router.post("/semantic-retrieval")
async def semantic_retrieval(request: SemanticRetrievalRequest, user_id: str = Depends(require_verified_email)):
    try:
        retriever = _get_retriever(user_id)
        results = retriever.retrieve(query=request.query, top_k=request.top_k)
        return {
            "query": request.query,
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "content": r.content,
                    "score": r.score,
                    "source": r.source,
                    "rank": r.rank,
                }
                for r in results
            ],
            "total": len(results),
        }
    except Exception as _e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(_e)) from None
