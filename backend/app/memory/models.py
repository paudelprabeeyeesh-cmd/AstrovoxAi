"""Pydantic models for conversation memory."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MemoryBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    metadata: Optional[dict] = Field(default_factory=dict)
    model_config = ConfigDict(from_attributes=True)


class MemoryCreate(MemoryBase):
    conversation_id: Optional[str] = None
    user_id: str
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    metadata: Optional[dict] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)


class MemoryResponse(MemoryBase):
    id: str
    conversation_id: Optional[str]
    user_id: str
    importance: float
    created_at: datetime
    updated_at: Optional[datetime] = None


class MemorySearch(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)
    conversation_id: Optional[str] = None


class MemorySummary(BaseModel):
    total_memories: int
    total_conversations: int
    avg_importance: float
    recent_memories: list[MemoryResponse]
