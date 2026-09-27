"""API keys API router."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .models import APIKeyCreate, APIKeyResponse, APIKeyUsage, APIKeyListResponse
from .service import APIKeyService

logger = logging.getLogger(__name__)
api_key_service = APIKeyService()
router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class MessageResponse(BaseModel):
    message: str


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(body: APIKeyCreate, user_id: str = Depends(lambda: "user-1")):
    record = api_key_service.create_key(user_id, body.name, body.scopes, body.expires_in_days)
    return APIKeyResponse(
        id=record["id"],
        key=record["key"],
        user_id=record["user_id"],
        name=record["name"],
        scopes=record["scopes"],
        created_at=record["created_at"],
        last_used=record["last_used"],
        expires_at=record["expires_at"],
        usage_count=record["usage_count"],
    )


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(user_id: str = Depends(lambda: "user-1")):
    keys = api_key_service.list_keys(user_id)
    return APIKeyListResponse(keys=keys, total=len(keys))


@router.delete("/{key_id}", response_model=MessageResponse)
async def revoke_api_key(key_id: str, user_id: str = Depends(lambda: "user-1")):
    if not api_key_service.revoke_key(key_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return MessageResponse(message="API key revoked successfully")


@router.get("/{key_id}/usage", response_model=list[APIKeyUsage])
async def get_api_key_usage(key_id: str, limit: int = 100):
    return api_key_service.get_usage(key_id, limit)
