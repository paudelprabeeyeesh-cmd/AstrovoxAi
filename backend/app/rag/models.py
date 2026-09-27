"""Pydantic models for RAG."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    metadata: Optional[dict] = Field(default_factory=dict)
    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    metadata: Optional[dict] = None


class DocumentResponse(DocumentBase):
    id: str
    user_id: str
    chunk_count: int
    created_at: datetime


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=50)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    document_id: str
    document_title: str
    chunk: str
    similarity: float
    metadata: dict


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
