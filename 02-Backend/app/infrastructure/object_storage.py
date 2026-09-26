"""Object storage abstraction with S3 and MinIO support."""

from __future__ import annotations

import logging
from typing import BinaryIO, Dict, List, Optional

from app.infrastructure.storage import get_storage

logger = logging.getLogger(__name__)


class ObjectStorage:
    """High-level object storage operations."""

    def __init__(self) -> None:
        self._storage = get_storage()
        self._default_bucket = "astrovox-storage"

    def upload_user_file(self, user_id: str, filename: str, data: BinaryIO, content_type: Optional[str] = None) -> str:
        key = f"uploads/{user_id}/{filename}"
        return self._storage.upload_file(self._default_bucket, key, data, content_type)

    def download_user_file(self, user_id: str, filename: str) -> bytes:
        key = f"uploads/{user_id}/{filename}"
        return self._storage.download_file(self._default_bucket, key)

    def get_user_file_url(self, user_id: str, filename: str, expires_in: int = 3600) -> str:
        key = f"uploads/{user_id}/{filename}"
        return self._storage.get_presigned_url(self._default_bucket, key, expires_in)

    def delete_user_file(self, user_id: str, filename: str) -> None:
        key = f"uploads/{user_id}/{filename}"
        self._storage.delete_file(self._default_bucket, key)

    def list_user_files(self, user_id: str) -> List[str]:
        prefix = f"uploads/{user_id}/"
        return self._storage.list_files(self._default_bucket, prefix)

    def upload_avatar(self, user_id: str, data: BinaryIO, content_type: str = "image/png") -> str:
        key = f"avatars/{user_id}/avatar.png"
        return self._storage.upload_file(self._default_bucket, key, data, content_type)

    def upload_document(self, doc_id: str, data: BinaryIO, content_type: str = "application/pdf") -> str:
        key = f"documents/{doc_id}/document.pdf"
        return self._storage.upload_file(self._default_bucket, key, data, content_type)


_storage: Optional[ObjectStorage] = None


def get_object_storage() -> ObjectStorage:
    global _storage
    if _storage is None:
        _storage = ObjectStorage()
    return _storage
