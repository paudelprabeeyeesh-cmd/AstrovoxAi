import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import UploadFile

from ASTROVOX_AI.ai_core.image import ImageAIPipelines

logger = logging.getLogger(__name__)

_image_pipelines: Optional[ImageAIPipelines] = None


def get_image_pipelines() -> ImageAIPipelines:
    global _image_pipelines
    if _image_pipelines is None:
        device = os.getenv("ASTROVOX_IMAGE_DEVICE", "cpu")
        _image_pipelines = ImageAIPipelines(device=device)
    return _image_pipelines


def _save_image_record(conn, user_id: str, kind: str, prompt: str = "", metadata: Dict[str, Any] = None) -> str:
    record_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO images (id, user_id, prompt, size, created_at, metadata) VALUES (?, ?, ?, ?, ?, ?)",
        (
            record_id,
            user_id,
            prompt[:1000],
            "0x0",
            datetime.now(timezone.utc).isoformat(),
            str(metadata or {}),
        ),
    )
    conn.commit()
    return record_id


class ImageAIService:
    def __init__(self, db_client=None):
        self.db = db_client

    async def text_to_image(self, user_id: str, prompt: str, **kwargs) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        result = pipelines.text_to_image(prompt, **kwargs)
        record_id = None
        if result.success and self.db:
            record_id = _save_image_record(self.db, user_id, "text_to_image", prompt, {"width": kwargs.get("width"), "height": kwargs.get("height")})
        return {
            "success": result.success,
            "id": record_id,
            "data": base64.b64encode(result.data).decode("utf-8") if result.data else "",
            "mime_type": result.mime_type,
            "metadata": result.metadata,
            "error": result.error,
        }

    async def image_to_image(self, user_id: str, file: UploadFile, prompt: str, **kwargs) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        content = await file.read()
        result = pipelines.image_to_image(content, prompt, **kwargs)
        record_id = None
        if result.success and self.db:
            record_id = _save_image_record(self.db, user_id, "image_to_image", prompt, {"filename": file.filename})
        return {
            "success": result.success,
            "id": record_id,
            "data": base64.b64encode(result.data).decode("utf-8") if result.data else "",
            "mime_type": result.mime_type,
            "metadata": result.metadata,
            "error": result.error,
        }

    async def inpaint(self, user_id: str, image_file: UploadFile, mask_file: UploadFile, prompt: str, **kwargs) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        image_bytes = await image_file.read()
        mask_bytes = await mask_file.read()
        result = pipelines.inpaint(image_bytes, mask_bytes, prompt, **kwargs)
        record_id = None
        if result.success and self.db:
            record_id = _save_image_record(self.db, user_id, "inpaint", prompt, {"image": image_file.filename, "mask": mask_file.filename})
        return {
            "success": result.success,
            "id": record_id,
            "data": base64.b64encode(result.data).decode("utf-8") if result.data else "",
            "mime_type": result.mime_type,
            "metadata": result.metadata,
            "error": result.error,
        }

    async def outpaint(self, user_id: str, file: UploadFile, expand: Dict[str, int], prompt: str, **kwargs) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        content = await file.read()
        result = pipelines.outpaint(
            content,
            expand_top=expand.get("top", 0),
            expand_bottom=expand.get("bottom", 0),
            expand_left=expand.get("left", 0),
            expand_right=expand.get("right", 0),
            prompt=prompt,
            **kwargs,
        )
        record_id = None
        if result.success and self.db:
            record_id = _save_image_record(self.db, user_id, "outpaint", prompt, {"expand": expand, "filename": file.filename})
        return {
            "success": result.success,
            "id": record_id,
            "data": base64.b64encode(result.data).decode("utf-8") if result.data else "",
            "mime_type": result.mime_type,
            "metadata": result.metadata,
            "error": result.error,
        }

    async def remove_background(self, user_id: str, file: UploadFile) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        content = await file.read()
        result = pipelines.remove_background(content)
        record_id = None
        if result.success and self.db:
            record_id = _save_image_record(self.db, user_id, "remove_background", metadata={"filename": file.filename})
        return {
            "success": result.success,
            "id": record_id,
            "data": base64.b64encode(result.data).decode("utf-8") if result.data else "",
            "mime_type": result.mime_type,
            "metadata": result.metadata,
            "error": result.error,
        }

    async def restore_face(self, user_id: str, file: UploadFile) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        content = await file.read()
        result = pipelines.restore_face(content)
        record_id = None
        if result.success and self.db:
            record_id = _save_image_record(self.db, user_id, "restore_face", metadata={"filename": file.filename})
        return {
            "success": result.success,
            "id": record_id,
            "data": base64.b64encode(result.data).decode("utf-8") if result.data else "",
            "mime_type": result.mime_type,
            "metadata": result.metadata,
            "error": result.error,
        }

    async def super_resolve(self, user_id: str, file: UploadFile, scale: int = 4) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        content = await file.read()
        result = pipelines.super_resolve(content, scale=scale)
        record_id = None
        if result.success and self.db:
            record_id = _save_image_record(self.db, user_id, "super_resolve", metadata={"scale": scale, "filename": file.filename})
        return {
            "success": result.success,
            "id": record_id,
            "data": base64.b64encode(result.data).decode("utf-8") if result.data else "",
            "mime_type": result.mime_type,
            "metadata": result.metadata,
            "error": result.error,
        }

    async def ocr(self, user_id: str, file: UploadFile, languages: Optional[List[str]] = None) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        content = await file.read()
        result = pipelines.ocr(content, languages=languages)
        return {
            "success": "error" not in result,
            "text": result.get("text", ""),
            "blocks": result.get("blocks", []),
            "error": result.get("error"),
        }

    async def detect_objects(self, user_id: str, file: UploadFile, threshold: float = 0.5) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        content = await file.read()
        result = pipelines.detect_objects(content, threshold=threshold)
        return {
            "success": "error" not in result,
            "objects": result.get("objects", []),
            "error": result.get("error"),
        }

    async def segment(self, user_id: str, file: UploadFile) -> Dict[str, Any]:
        pipelines = get_image_pipelines()
        content = await file.read()
        result = pipelines.segment(content)
        return {
            "success": "error" not in result,
            "segments": result.get("segments", []),
            "error": result.get("error"),
        }
