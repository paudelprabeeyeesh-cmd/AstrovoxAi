import os
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from .logging_config import logger
from .supabase_client import get_supabase

router = APIRouter(prefix="/storage", tags=["storage"])


class StorageService:
    """Persist files locally and optionally through Supabase Storage."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.getenv("STORAGE_ROOT", "./storage"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_path(self, user_id: str, bucket: str, path: str) -> Path:
        safe_path = unquote(path).replace("\\", "/")
        if safe_path.startswith("/"):
            safe_path = safe_path[1:]
        if ".." in Path(safe_path).parts:
            raise ValueError("Invalid path traversal")
        if not safe_path.startswith(f"user/{user_id}/") and not safe_path.startswith(f"users/{user_id}/"):
            raise ValueError("Path does not belong to the authenticated user")
        target = self.base_dir / bucket / safe_path
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def upload_file(
        self,
        user_id: str,
        bucket: str,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
    ) -> dict:
        target = self._normalize_path(user_id, bucket, path)
        target.write_bytes(content)
        return {
            "bucket": bucket,
            "path": str(target.relative_to(self.base_dir / bucket)),
            "content_type": content_type or "application/octet-stream",
            "size": len(content),
        }

    def delete_file(self, user_id: str, bucket: str, path: str) -> bool:
        target = self._normalize_path(user_id, bucket, path)
        if target.exists():
            target.unlink()
            return True
        return False

    def get_signed_url(self, user_id: str, bucket: str, path: str) -> dict:
        target = self._normalize_path(user_id, bucket, path)
        return {
            "bucket": bucket,
            "path": str(target.relative_to(self.base_dir / bucket)),
            "url": f"/storage/{bucket}/{target.relative_to(self.base_dir / bucket).as_posix()}?download=1",
        }


storage_service = StorageService()


@router.post("/{bucket}/upload")
async def upload_storage_file(
    bucket: str,
    file: UploadFile = File(...),
    user_id: str = "",
    path: str = "",
):
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
    try:
        content = await file.read()
        result = storage_service.upload_file(
            user_id,
            bucket,
            path or file.filename or "upload.bin",
            content,
            content_type=file.content_type,
        )
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"status": "OK", **result})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        logger.exception("Storage upload failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete("/{bucket}/{path:path}")
async def delete_storage_file(bucket: str, path: str, user_id: str):
    try:
        deleted = storage_service.delete_file(user_id, bucket, path)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return {"status": "OK", "deleted": True}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{bucket}/{path:path}/signed-url")
async def signed_url(bucket: str, path: str, user_id: str):
    try:
        return {"status": "OK", **storage_service.get_signed_url(user_id, bucket, path)}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
