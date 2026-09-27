"""Pydantic models for API keys."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class APIKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)
    model_config = ConfigDict(from_attributes=True)


class APIKeyCreate(APIKeyBase):
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(APIKeyBase):
    id: str
    key: str
    user_id: str
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    usage_count: int = 0


class APIKeyUsage(BaseModel):
    api_key_id: str
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    timestamp: datetime


class APIKeyListResponse(BaseModel):
    keys: list[APIKeyResponse]
    total: int
