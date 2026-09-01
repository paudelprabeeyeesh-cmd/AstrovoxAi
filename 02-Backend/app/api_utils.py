"""API Maturity — pagination, error normalization, and response standards."""

from typing import Optional
from fastapi import Request, HTTPException, status
from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    """Standard paginated response."""
    items: list
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class APIError(BaseModel):
    """Standard error response."""
    error: str
    code: str
    detail: str = ""
    request_id: str = ""


class APIResponse(BaseModel):
    """Standard success response."""
    status: str = "OK"
    data: Optional[dict] = None
    message: str = ""


def paginate(
    items: list,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse:
    """Paginate a list of items."""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    return PaginatedResponse(
        items=page_items,
        total=len(items),
        page=page,
        page_size=page_size,
        has_next=end < len(items),
        has_prev=page > 1,
    )


def create_error_response(
    error: str,
    code: str,
    detail: str = "",
    request_id: str = "",
) -> dict:
    """Create a standardized error response."""
    return {
        "status": "error",
        "error": APIError(
            error=error,
            code=code,
            detail=detail,
            request_id=request_id,
        ).model_dump(),
    }


def create_success_response(data: Optional[dict] = None, message: str = "") -> dict:
    """Create a standardized success response."""
    return {
        "status": "OK",
        "data": data,
        "message": message,
    }


class APIException(HTTPException):
    """Standardized API exception."""

    def __init__(
        self,
        status_code: int,
        error: str,
        code: str,
        detail: str = "",
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error = error
        self.code = code
