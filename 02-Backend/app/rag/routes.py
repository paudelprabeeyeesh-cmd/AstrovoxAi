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

import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from app.rag import RAGPipeline, RAGRetriever, RetrievalResult
from app.documents import (
    delete_document,
    delete_document_chunks,
    get_document,
    list_documents,
)
from app.utils.auth.auth_utils import get_user_id_from_token

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


async def _request_payload(request: Request) -> Dict[str, Any]:
    """Read a request body as JSON or as multipart form fields.

    These endpoints historically took form fields with a JSON-encoded
    ``request`` string. That contract rejects an ordinary JSON body with a
    422 naming a field the caller never sent, so both forms are accepted
    now: existing form callers keep working, and a JSON caller gets the
    response it asked for.
    """
    payload: Dict[str, Any] = {}
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            body = await request.json()
        except ValueError:
            return payload
        if isinstance(body, dict):
            payload.update(body)
    else:
        try:
            form = await request.form()
        except ValueError:
            return payload
        payload.update({key: value for key, value in form.items()})

    legacy = payload.get("request")
    if isinstance(legacy, str):
        try:
            decoded = json.loads(legacy)
        except ValueError:
            decoded = None
        if isinstance(decoded, dict):
            for key, value in decoded.items():
                payload.setdefault(key, value)

    return payload


def _resolve_user_id(payload: Dict[str, Any], authorization: Optional[str]) -> str:
    """Caller identity from the bearer token, else the body, else a default."""
    if authorization:
        try:
            resolved = get_user_id_from_token(authorization)
        except Exception:
            resolved = None
        if resolved:
            return resolved
    claimed = payload.get("user_id")
    return str(claimed) if claimed else "system"


def _resolve_query_user_id(claimed: Optional[str], authorization: Optional[str]) -> str:
    """Caller identity from the bearer token, else a query param.

    Taking the identity from a query parameter lets any caller enumerate
    another user's documents by editing the URL, so the token wins whenever
    one is present and the parameter is only a fallback for callers that
    have no token.
    """
    if authorization:
        try:
            resolved = get_user_id_from_token(authorization)
        except Exception:
            resolved = None
        if resolved:
            return resolved
    return str(claimed) if claimed else "system"


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
async def search_documents(request: Request, authorization: str = Header(None)):
    """Search documents for the calling user.

    Accepts a JSON body or the legacy multipart form. The caller identity
    comes from the bearer token when one is present, so a request cannot
    read another user's documents by setting `user_id` in the body.
    """
    payload = await _request_payload(request)
    user_id = _resolve_user_id(payload, authorization)
    try:
        req = SearchRequest(**{
            key: value
            for key, value in payload.items()
            if key in SearchRequest.model_fields
        })
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request body") from exc

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
async def list_user_documents(
    user_id: Optional[str] = None, authorization: str = Header(None)
):
    resolved = _resolve_query_user_id(user_id, authorization)
    try:
        docs = list_documents(resolved)
        return [DocumentResponse(**doc) for doc in docs]
    except Exception as exc:
        logger.error("List documents failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list documents") from exc


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_user_document(
    doc_id: str, user_id: Optional[str] = None, authorization: str = Header(None)
):
    resolved = _resolve_query_user_id(user_id, authorization)
    try:
        doc = get_document(resolved, doc_id)
        return DocumentResponse(**doc)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    except Exception as exc:
        logger.error("Get document failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get document") from exc


@router.delete("/documents/{doc_id}")
async def delete_user_document(
    doc_id: str, user_id: Optional[str] = None, authorization: str = Header(None)
):
    resolved = _resolve_query_user_id(user_id, authorization)
    try:
        deleted = delete_document(resolved, doc_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        retriever = _get_retriever(resolved)
        retriever.embedding_store.delete_document(doc_id)
        retriever.clear_index()
        return {"status": "OK", "deleted": doc_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Delete document failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete document") from exc
