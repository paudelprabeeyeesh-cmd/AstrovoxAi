from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    components: dict
    timestamp: str


@router.get("/", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        components={"database": {"status": "healthy", "message": "Connected"}},
        timestamp=datetime.now().isoformat(),
    )


@router.get("/readiness")
async def readiness_check():
    return {"status": "ready", "timestamp": datetime.now().isoformat()}


@router.get("/liveness")
async def liveness_check():
    return {"status": "alive", "timestamp": datetime.now().isoformat()}
