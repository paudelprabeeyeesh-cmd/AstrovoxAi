"""Standardized error response schema for consistent API error payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    target: Optional[str] = Field(default=None, description="Field or resource the error applies to")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional structured details")


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: Optional[str] = Field(default=None, description="Correlation ID for support")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def build_error_response(
    code: str,
    message: str,
    status_code: int = 400,
    *,
    target: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message, target=target, details=details),
        request_id=request_id,
    ).model_dump()
    # strip None values for compactness
    if payload.get("request_id") is None:
        del payload["request_id"]
    return payload


ERROR_CODES = {
    "validation_error": "VALIDATION_ERROR",
    "not_found": "NOT_FOUND",
    "unauthorized": "UNAUTHORIZED",
    "forbidden": "FORBIDDEN",
    "conflict": "CONFLICT",
    "rate_limit": "RATE_LIMIT_EXCEEDED",
    "internal": "INTERNAL_ERROR",
    "bad_request": "BAD_REQUEST",
    "unprocessable": "UNPROCESSABLE_ENTITY",
}
