"""File upload API router."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .models import UploadResponse, UploadMetadata, DocumentParseRequest, ParsedDocument
from .service import UploadService

logger = logging.getLogger(__name__)
upload_service = UploadService()
router = APIRouter(prefix="/uploads", tags=["uploads"])


class MessageResponse(BaseModel):
    message: str


@router.post("/", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(filename: str, content_type: str, content: bytes, user_id: str = Depends(lambda: "user-1")):
    return upload_service.save_upload(user_id, filename, content, content_type)


@router.get("/{upload_id}", response_model=UploadResponse)
async def get_upload(upload_id: str):
    upload = upload_service.get_upload(upload_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return upload


@router.post("/{upload_id}/parse", response_model=ParsedDocument)
async def parse_upload(upload_id: str, body: DocumentParseRequest):
    result = upload_service.parse_document(upload_id, body.extract_images)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return ParsedDocument(upload_id=upload_id, **result)


@router.delete("/{upload_id}", response_model=MessageResponse)
async def delete_upload(upload_id: str):
    if not upload_service.delete_upload(upload_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return MessageResponse(message="Upload deleted successfully")
