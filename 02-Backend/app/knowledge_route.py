"""Knowledge Base API routes — document upload and search."""

from fastapi import APIRouter, HTTPException, status, Header, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional

from .knowledge_base import knowledge_base
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class UploadRequest(BaseModel):
    filename: str
    content: str
    file_type: str = "text"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)


@router.post("/upload")
async def upload_document(request: UploadRequest, authorization: str = Header(None)):
    """Upload a document to the knowledge base."""
    user_id = get_user_id_from_token(authorization)

    document = await knowledge_base.upload_document(
        user_id=user_id,
        filename=request.filename,
        content=request.content,
        file_type=request.file_type,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document",
        )

    return {
        "status": "OK",
        "document": {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "chunk_count": document.chunk_count,
            "created_at": document.created_at,
        },
    }


@router.post("/search")
async def search_knowledge(request: SearchRequest, authorization: str = Header(None)):
    """Search the knowledge base."""
    user_id = get_user_id_from_token(authorization)

    results = await knowledge_base.search(
        user_id=user_id,
        query=request.query,
        limit=request.limit,
    )

    return {
        "status": "OK",
        "results": [
            {
                "content": r.chunk.content,
                "score": round(r.score, 4),
                "document_id": r.chunk.document_id,
                "filename": r.document.filename if r.document else None,
            }
            for r in results
        ],
        "count": len(results),
    }


@router.get("/documents")
async def list_documents(authorization: str = Header(None)):
    """List user's documents."""
    user_id = get_user_id_from_token(authorization)
    documents = knowledge_base.get_user_documents(user_id)

    return {
        "status": "OK",
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "file_type": d.file_type,
                "chunk_count": d.chunk_count,
                "created_at": d.created_at,
            }
            for d in documents
        ],
        "count": len(documents),
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, authorization: str = Header(None)):
    """Delete a document."""
    user_id = get_user_id_from_token(authorization)

    success = knowledge_base.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return {"status": "OK", "message": "Document deleted"}


@router.get("/stats")
async def get_knowledge_stats(authorization: str = Header(None)):
    """Get knowledge base statistics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "stats": knowledge_base.get_stats(user_id)}
