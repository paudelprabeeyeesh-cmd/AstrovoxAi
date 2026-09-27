"""Pydantic models for file uploads."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UploadMetadata(BaseModel):
    filename: str
    content_type: str
    size: int
    model_config = ConfigDict(from_attributes=True)


class UploadResponse(UploadMetadata):
    id: str
    user_id: str
    uploaded_at: datetime
    url: Optional[str] = None
    parsed: bool = False


class DocumentParseRequest(BaseModel):
    upload_id: str
    extract_images: bool = Field(default=False)
    chunk_size: int = Field(default=1000, ge=100, le=10000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)


class ParsedDocument(BaseModel):
    upload_id: str
    text: str
    chunks: list[str]
    metadata: dict
