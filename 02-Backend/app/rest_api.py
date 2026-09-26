"""REST API endpoints and utilities."""

from typing import Any, Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()


class RESTResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


@router.get("/api/v1/health", response_model=RESTResponse)
async def rest_health():
    return RESTResponse(success=True, data={"status": "ok"})


@router.get("/api/v1/status", response_model=RESTResponse)
async def rest_status():
    return RESTResponse(success=True, data={"version": "2.0.0", "service": "astrovox-ai"})


class RESTErrorHandler:
    @staticmethod
    def not_found(message: str = "Resource not found") -> HTTPException:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

    @staticmethod
    def bad_request(message: str = "Bad request") -> HTTPException:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> HTTPException:
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

    @staticmethod
    def forbidden(message: str = "Forbidden") -> HTTPException:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    @staticmethod
    def internal_error(message: str = "Internal server error") -> HTTPException:
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
