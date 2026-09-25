import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..storage import storage_service
from ..auth import require_verified_email, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["files"])


@router.post("/files/upload")
async def upload_file_endpoint(file: UploadFile = File(...), user_id: str = Depends(require_verified_email)):
    file_bytes = await file.read()
    url = storage_service.upload_file(file_bytes, file.filename, user_id, file.content_type or "application/octet-stream")
    return {"url": url, "filename": file.filename}


@router.get("/files")
async def list_files_endpoint(user_id: str = Depends(get_current_user)):
    return storage_service.list_user_files(user_id)


@router.get("/files/{file_id}")
async def get_file_endpoint(file_id: str, user_id: str = Depends(get_current_user)):
    return {"url": storage_service.get_file_url(file_id, user_id)}


@router.delete("/files/{file_id}")
async def delete_file_endpoint(file_id: str, user_id: str = Depends(require_verified_email)):
    if not storage_service.delete_file(file_id, user_id):
        raise HTTPException(status_code=404, detail="File not found")
    return {"ok": True}
