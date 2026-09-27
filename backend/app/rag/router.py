"""RAG API router."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .models import DocumentCreate, DocumentResponse, DocumentSearchRequest, SearchResponse
from .service import RAGService

logger = logging.getLogger(__name__)
rag_service = RAGService()
router = APIRouter(prefix="/rag", tags=["rag"])


class MessageResponse(BaseModel):
    message: str


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(body: DocumentCreate, user_id: str = Depends(lambda: "user-1")):
    doc = rag_service.ingest_document(user_id, body.title, body.content, body.metadata)
    return DocumentResponse(id=doc["id"], title=doc["title"], user_id=doc["user_id"], created_at=doc["created_at"], chunk_count=len(doc["chunks"]))


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(user_id: str = Depends(lambda: "user-1")):
    return rag_service.list_documents(user_id)


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    doc = rag_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse(id=doc["id"], title=doc["title"], user_id=doc["user_id"], created_at=doc["created_at"], chunk_count=len(doc["chunks"]))


@router.delete("/documents/{doc_id}", response_model=MessageResponse)
async def delete_document(doc_id: str):
    if not rag_service.delete_document(doc_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return MessageResponse(message="Document deleted successfully")


@router.post("/search", response_model=SearchResponse)
async def search_documents(body: DocumentSearchRequest, user_id: str = Depends(lambda: "user-1")):
    results = rag_service.search(body.query, user_id, body.limit, body.min_similarity)
    return SearchResponse(query=body.query, results=results, total=len(results))
