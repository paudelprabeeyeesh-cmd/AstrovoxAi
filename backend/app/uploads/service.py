"""File upload service."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from .parser import DocumentParser

logger = logging.getLogger(__name__)


class UploadService:
    def __init__(self, storage_root: str = "./storage") -> None:
        self._storage_root = storage_root
        self._uploads: dict[str, dict] = {}
        self._parser = DocumentParser()
        os.makedirs(storage_root, exist_ok=True)

    def save_upload(self, user_id: str, filename: str, content: bytes, content_type: str) -> dict:
        upload_id = str(uuid.uuid4())
        ext = os.path.splitext(filename)[1]
        safe_filename = f"{upload_id}{ext}"
        filepath = os.path.join(self._storage_root, safe_filename)
        with open(filepath, "wb") as f:
            f.write(content)
        now = datetime.now(timezone.utc).isoformat()
        upload = {
            "id": upload_id,
            "user_id": user_id,
            "filename": filename,
            "content_type": content_type,
            "size": len(content),
            "path": filepath,
            "url": f"/uploads/{safe_filename}",
            "parsed": False,
            "uploaded_at": now,
        }
        self._uploads[upload_id] = upload
        return upload

    def get_upload(self, upload_id: str) -> Optional[dict]:
        return self._uploads.get(upload_id)

    def parse_document(self, upload_id: str, extract_images: bool = False) -> Optional[dict]:
        upload = self._uploads.get(upload_id)
        if not upload:
            return None
        with open(upload["path"], "rb") as f:
            content = f.read()
        parsed = self._parser.parse(content, upload["content_type"], upload["filename"])
        upload["parsed"] = True
        return parsed

    def delete_upload(self, upload_id: str) -> bool:
        upload = self._uploads.pop(upload_id, None)
        if not upload:
            return False
        try:
            os.remove(upload["path"])
        except OSError:
            pass
        return True
