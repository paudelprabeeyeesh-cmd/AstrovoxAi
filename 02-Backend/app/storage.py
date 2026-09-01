import os
import re
import secrets
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, File, HTTPException, UploadFile, status, Header
from fastapi.responses import JSONResponse

from .logging_config import logger
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/storage", tags=["storage"])

ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "application/pdf",
    "text/plain",
}

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".txt"}

ALLOWED_BUCKETS = {"avatars", "documents", "uploads", "attachments"}

MAX_UPLOAD_SIZE = 5 * 1024 * 1024


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and injection."""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    if not filename or filename.startswith('.'):
        filename = f"file_{secrets.token_hex(8)}{filename}"
    name, ext = os.path.splitext(filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        ext = ".bin"
    return f"{name}_{secrets.token_hex(4)}{ext}"


def verify_magic_bytes(content: bytes, content_type: str) -> bool:
    """Verify file magic bytes match claimed content type."""
    magic_map = {
        "image/png": content[:8] == b'\x89PNG\r\n\x1a\n',
        "image/jpeg": content[:3] == b'\xff\xd8\xff',
        "image/webp": content[:4] == b'RIFF',
        "application/pdf": content[:5] == b'%PDF-',
        "text/plain": all(32 <= b < 127 or b in (10, 13, 9) for b in content[:100]),
    }
    return magic_map.get(content_type, True)


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
        if not safe_path.startswith(f"user/{user_id}/") and not safe_path.startswith(
            f"users/{user_id}/"
        ):
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
    path: str = "",
    authorization: str = Header(None),
):
    user_id = get_user_id_from_token(authorization)

    # Validate bucket allowlist
    if bucket not in ALLOWED_BUCKETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bucket",
        )

    try:
        content = await file.read()

        # Validate file size
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large",
            )

        # Validate content type
        if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported content type",
            )

        # Verify magic bytes match claimed content type
        if not verify_magic_bytes(content, file.content_type or ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match claimed type",
            )

        # Sanitize and generate random filename
        safe_filename = sanitize_filename(file.filename or "upload.bin")

        result = storage_service.upload_file(
            user_id,
            bucket,
            path or safe_filename,
            content,
            content_type=file.content_type,
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED, content={"status": "OK", **result}
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(f"Storage upload access denied: {str(exc)[:100]}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc
    except Exception as exc:
        logger.exception("Storage upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Upload failed"
        ) from exc


@router.delete("/{bucket}/{path:path}")
async def delete_storage_file(bucket: str, path: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    try:
        deleted = storage_service.delete_file(user_id, bucket, path)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )
        return {"status": "OK", "deleted": True}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.get("/{bucket}/{path:path}/signed-url")
async def signed_url(bucket: str, path: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    try:
        return {"status": "OK", **storage_service.get_signed_url(user_id, bucket, path)}
    except ValueError as exc:
        logger.warning(f"Storage signed-url access denied: {str(exc)[:100]}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc
