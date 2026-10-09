"""
RAG API routes - document ingestion and retrieval.

Endpoints:
- POST /rag/ingest/text - Ingest raw text
- POST /rag/ingest/file - Ingest uploaded file
- POST /rag/ingest/website - Ingest website
- POST /rag/ingest/github - Ingest GitHub repo
- POST /rag/search - Search documents
- GET /rag/documents - List user documents
- GET /rag/documents/{doc_id} - Get document
- DELETE /rag/documents/{doc_id} - Delete document
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.rag import RAGPipeline, RAGRetriever, RetrievalResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])

_rag_pipelines: Dict[str, RAGPipeline] = {}
_rag_retrievers: Dict[str, RAGRetriever] = {}


def _get_pipeline(user_id: str) -> RAGPipeline:
    if user_id not in _rag_pipelines:
        _rag_pipelines[user_id] = RAGPipeline(user_id=user_id)
    return _rag_pipelines[user_id]


def _get_retriever(user_id: str) -> RAGRetriever:
    if user_id not in _rag_retrievers:
        retriever = RAGRetriever()
        _rag_retrievers[user_id] = retriever
    return _rag_retrievers[user_id]


class IngestTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000)
    filename: str = Field(default="text", max_length=255)
    source_type: str = Field(default="txt", max_length=50)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestWebsiteRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2000)
    filename: str = Field(default="website", max_length=255)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestGithubRequest(BaseModel):
    repo_url: str = Field(..., min_length=1, max_length=2000)
    filename: str = Field(default="github_repo", max_length=255)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    metadata_filter: Dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    source_type: str
    size: int
    created_at: str


class ChunkResponse(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    source: str
    rank: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    source_type: str
    chunks_created: int
    total_characters: int
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/ingest/text", response_model=IngestResponse)
async def ingest_text(user_id: str = Form(...), request: str = Form(...)):
    try:
        import json
        body = json.loads(request) if isinstance(request, str) else request
        req = IngestTextRequest(**body)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request body")

    pipeline = _get_pipeline(user_id)
    try:
        result = await pipeline.ingest_text(
            text=req.text,
            filename=req.filename,
            source_type=req.source_type,
            metadata=req.metadata,
        )
        return IngestResponse(
            document_id=result.document_id,
            filename=result.filename,
            source_type=result.source_type,
            chunks_created=result.chunks_created,
            total_characters=result.total_characters,
            created_at=result.created_at,
            metadata=result.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Text ingestion failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ingestion failed") from exc


@router.post("/ingest/file", response_model=IngestResponse)
async def ingest_file(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    metadata: str = Form("{}"),
):
    pipeline = _get_pipeline(user_id)
    try:
        import json
        file_metadata = json.loads(metadata) if metadata else {}
    except Exception:
        file_metadata = {}
    suffix = os.path.splitext(file.filename or "upload")[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = await pipeline.ingest_file(
            file_path=tmp_path,
            filename=file.filename or "upload",
            metadata=file_metadata,
        )
        return IngestResponse(
            document_id=result.document_id,
            filename=result.filename,
            source_type=result.source_type,
            chunks_created=result.chunks_created,
            total_characters=result.total_characters,
            created_at=result.created_at,
            metadata=result.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("File ingestion failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ingestion failed") from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@router.post("/ingest/website", response_model=IngestResponse)
async def ingest_website(user_id: str = Form(...), request: str = Form(...)):
    try:
        import json
        body = json.loads(request) if isinstance(request, str) else request
        req = IngestWebsiteRequest(**body)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request body")

    pipeline = _get_pipeline(user_id)
    try:
        result = await pipeline.ingest_website(
            url=req.url,
            filename=req.filename,
            metadata=req.metadata,
        )
        return IngestResponse(
            document_id=result.document_id,
            filename=result.filename,
            source_type=result.source_type,
            chunks_created=result.chunks_created,
            total_characters=result.total_characters,
            created_at=result.created_at,
            metadata=result.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Website ingestion failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ingestion failed") from exc


@router.post("/ingest/github", response_model=IngestResponse)
async def ingest_github(user_id: str = Form(...), request: str = Form(...)):
    try:
        import json
        body = json.loads(request) if isinstance(request, str) else request
        req = IngestGithubRequest(**body)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request body")

    pipeline = _get_pipeline(user_id)
    try:
        result = await pipeline.ingest_github_repo(
            repo_url=req.repo_url,
            filename=req.filename,
            metadata=req.metadata,
        )
        return IngestResponse(
            document_id=result.document_id,
            filename=result.filename,
            source_type=result.source_type,
            chunks_created=result.chunks_created,
            total_characters=result.total_characters,
            created_at=result.created_at,
            metadata=result.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("GitHub ingestion failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ingestion failed") from exc


@router.post("/search", response_model=List[ChunkResponse])
async def search_documents(user_id: str = Form(...), request: str = Form(...)):
    try:
        import json
        body = json.loads(request) if isinstance(request, str) else request
        req = SearchRequest(**body)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request body")

    retriever = _get_retriever(user_id)
    try:
        results = await retriever.retrieve(
            query=req.query,
            top_k=req.top_k,
            metadata_filter=req.metadata_filter or None,
        )
        if not results:
            results = await retriever.retrieve_from_db(
                query=req.query,
                top_k=req.top_k,
            )
        return [
            ChunkResponse(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                content=r.content,
                score=r.score,
                source=r.source,
                rank=r.rank,
                metadata=r.metadata,
            )
            for r in results
        ]
    except Exception as exc:
        logger.error("Search failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed") from exc


@router.get("/documents", response_model=List[DocumentResponse])
async def list_user_documents(user_id: str):
    try:
        docs = list_documents(user_id)
        return [DocumentResponse(**doc) for doc in docs]
    except Exception as exc:
        logger.error("List documents failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list documents") from exc


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_user_document(user_id: str, doc_id: str):
    try:
        doc = get_document(user_id, doc_id)
        return DocumentResponse(**doc)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    except Exception as exc:
        logger.error("Get document failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get document") from exc


@router.delete("/documents/{doc_id}")
async def delete_user_document(user_id: str, doc_id: str):
    try:
        deleted = delete_document(user_id, doc_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        retriever = _get_retriever(user_id)
        retriever.embedding_store.delete_document(doc_id)
        retriever.clear_index()
        return {"status": "OK", "deleted": doc_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Delete document failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete document") from exc
