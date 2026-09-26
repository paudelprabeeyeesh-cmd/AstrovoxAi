import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from ..auth import require_verified_email
from app.repositories.database.client import get_db
from ..image_ai import ImageAIService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["images"])


def _get_service() -> ImageAIService:
    return ImageAIService(db_client=get_db())


@router.post("/images/generate")
async def generate_image(
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    width: int = Form(1024),
    height: int = Form(1024),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    seed: Optional[int] = Form(None),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        result = await service.text_to_image(
            user_id,
            prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))
        return {
            "id": result["id"],
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "seed": seed,
            "data": result["data"],
            "mime_type": result["mime_type"],
            "metadata": result["metadata"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/transform/img2img")
async def image_to_image(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    strength: float = Form(0.75),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    seed: Optional[int] = Form(None),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        result = await service.image_to_image(
            user_id,
            file,
            prompt,
            negative_prompt=negative_prompt,
            strength=strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Image-to-image failed"))
        return {
            "id": result["id"],
            "prompt": prompt,
            "strength": strength,
            "data": result["data"],
            "mime_type": result["mime_type"],
            "metadata": result["metadata"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image-to-image failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/transform/inpaint")
async def inpaint_image(
    image_file: UploadFile = File(...),
    mask_file: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    seed: Optional[int] = Form(None),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        result = await service.inpaint(
            user_id,
            image_file,
            mask_file,
            prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Inpainting failed"))
        return {
            "id": result["id"],
            "prompt": prompt,
            "data": result["data"],
            "mime_type": result["mime_type"],
            "metadata": result["metadata"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inpainting failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/transform/outpaint")
async def outpaint_image(
    file: UploadFile = File(...),
    expand_top: int = Form(0),
    expand_bottom: int = Form(0),
    expand_left: int = Form(0),
    expand_right: int = Form(0),
    prompt: str = Form(""),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        result = await service.outpaint(
            user_id,
            file,
            {"top": expand_top, "bottom": expand_bottom, "left": expand_left, "right": expand_right},
            prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Outpainting failed"))
        return {
            "id": result["id"],
            "expand": {"top": expand_top, "bottom": expand_bottom, "left": expand_left, "right": expand_right},
            "data": result["data"],
            "mime_type": result["mime_type"],
            "metadata": result["metadata"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Outpainting failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/edit/remove-background")
async def remove_background(
    file: UploadFile = File(...),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        result = await service.remove_background(user_id, file)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Background removal failed"))
        return {
            "id": result["id"],
            "data": result["data"],
            "mime_type": result["mime_type"],
            "metadata": result["metadata"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Background removal failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/edit/restore-face")
async def restore_face(
    file: UploadFile = File(...),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        result = await service.restore_face(user_id, file)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Face restoration failed"))
        return {
            "id": result["id"],
            "data": result["data"],
            "mime_type": result["mime_type"],
            "metadata": result["metadata"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Face restoration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/edit/super-resolve")
async def super_resolve(
    file: UploadFile = File(...),
    scale: int = Form(4),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        result = await service.super_resolve(user_id, file, scale=scale)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Super resolution failed"))
        return {
            "id": result["id"],
            "scale": scale,
            "data": result["data"],
            "mime_type": result["mime_type"],
            "metadata": result["metadata"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Super resolution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/analyze/ocr")
async def analyze_ocr(
    file: UploadFile = File(...),
    languages: Optional[str] = Form(None),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        lang_list = languages.split(",") if languages else None
        result = await service.ocr(user_id, file, languages=lang_list)
        if "error" in result and result["error"]:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/analyze/detect-objects")
async def detect_objects(
    file: UploadFile = File(...),
    threshold: float = Form(0.5),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        result = await service.detect_objects(user_id, file, threshold=threshold)
        if "error" in result and result["error"]:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Object detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/analyze/segment")
async def segment_image(
    file: UploadFile = File(...),
    user_id: str = Depends(require_verified_email),
):
    try:
        service = _get_service()
        result = await service.segment(user_id, file)
        if "error" in result and result["error"]:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Segmentation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/{image_id}")
async def get_image(image_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, prompt, size, created_at, metadata FROM images WHERE id = ? AND user_id = ?",
            (image_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Image not found")
        return dict(row)
