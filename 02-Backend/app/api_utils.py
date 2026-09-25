"""API Maturity — pagination, field filtering, sparse responses, and response standards."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Union
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
    """Paginate a list of items with safe bounds."""
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


def filter_fields(data: Union[dict, list], fields: Optional[Set[str]]) -> Union[dict, list]:
    """Filter a dict or list of dicts to only the requested fields.

    If fields is empty or None, return data unchanged.
    """
    if not fields:
        return data

    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in fields}

    if isinstance(data, list):
        return [filter_fields(item, fields) for item in data if isinstance(item, dict)]

    return data


def parse_fields_param(fields_param: Optional[str]) -> Set[str]:
    """Parse a comma-separated fields parameter into a set of field names."""
    if not fields_param:
        return set()
    return {f.strip() for f in fields_param.split(",") if f.strip()}


def sparse_response(data: Any, fields: Optional[Set[str]]) -> Any:
    """Return a sparse response by filtering fields from nested data."""
    if not fields:
        return data
    return filter_fields(data, fields)


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