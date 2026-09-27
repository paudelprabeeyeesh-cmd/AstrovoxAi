"""FastAPI router for model management endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from .service import model_management_service

router = APIRouter(prefix="/model-factory", tags=["model-management"])


class ModelCreateRequest(BaseModel):
    name: str
    description: str = ""


@router.get("")
async def list_models():
    return model_management_service.list_models()


@router.post("")
async def create_model(request: ModelCreateRequest):
    return model_management_service.create_model(name=request.name, description=request.description)
