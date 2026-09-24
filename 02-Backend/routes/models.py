from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class ModelRegisterRequest(BaseModel):
    name: str
    provider: str
    model_id: str
    capabilities: List[str] = ["chat", "completion"]
    priority: int = 1


class ModelResponse(BaseModel):
    id: str
    name: str
    provider: str
    model_id: str
    capabilities: List[str]
    priority: int


models_store: dict[str, dict] = {}


def _generate_id() -> str:
    from datetime import datetime
    return f"model_{datetime.now().timestamp()}"


@router.get("/", response_model=List[ModelResponse])
async def list_models():
    return list(models_store.values())


@router.post("/register", response_model=ModelResponse)
async def register_model(request: ModelRegisterRequest):
    mid = _generate_id()
    model = {
        "id": mid,
        "name": request.name,
        "provider": request.provider,
        "model_id": request.model_id,
        "capabilities": request.capabilities,
        "priority": request.priority,
    }
    models_store[mid] = model
    return model


@router.get("/stats")
async def model_stats():
    return {
        "total": len(models_store),
        "providers": len({m["provider"] for m in models_store.values()}),
    }
