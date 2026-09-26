"""Standardized error response handler for FastAPI.

Wires into FastAPI exception handlers to return consistent error payloads
defined in `app.utils.error_schema`.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.error_schema import build_error_response, ERROR_CODES

logger = logging.getLogger("astravox.errors")


def _correlation_id(request: Request) -> Optional[str]:
    return getattr(request.state, "correlation_id", None)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = ERROR_CODES.get(
        {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            422: "unprocessable",
            429: "rate_limit",
            413: "payload_too_large",
            504: "internal",
            500: "internal",
        }.get(exc.status_code, "internal"),
        "INTERNAL_ERROR",
    )
    payload = build_error_response(
        code=code,
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=_correlation_id(request),
    )
    return JSONResponse(status_code=exc.status_code, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    payload = build_error_response(
        code="INTERNAL_ERROR",
        message="Internal server error",
        status_code=500,
        request_id=_correlation_id(request),
    )
    return JSONResponse(status_code=500, content=payload)


def register_error_handlers(app) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
