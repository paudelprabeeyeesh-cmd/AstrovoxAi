"""Standardized error response handler for FastAPI.

Wires into FastAPI exception handlers to return consistent error payloads
defined in `app.utils.error_schema`.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.error_schema import build_error_response, ERROR_CODES

logger = logging.getLogger("astravox.errors")


def _correlation_id(request: Request) -> Optional[str]:
    return getattr(request.state, "correlation_id", None)


def _emit_correlation_id(request: Request, response: JSONResponse) -> JSONResponse:
    """Put the correlation id on the response body and headers.

    The logging middleware sets `request.state.correlation_id` and adds the
    header to successful responses, but it cannot touch the response that an
    exception handler produces. Setting it here keeps the id available on
    error responses too, which is exactly when a caller needs to report it.
    """
    cid = _correlation_id(request)
    if cid:
        response.headers["X-Correlation-ID"] = cid
    return response


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
    return _emit_correlation_id(request, JSONResponse(status_code=exc.status_code, content=payload))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    payload = build_error_response(
        code="INTERNAL_ERROR",
        message="Internal server error",
        status_code=500,
        request_id=_correlation_id(request),
    )
    return _emit_correlation_id(request, JSONResponse(status_code=500, content=payload))


def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation errors in the same envelope as every other error."""
    fields = {}
    for err in exc.errors():
        location = ".".join(str(part) for part in err.get("loc", []))
        fields[location] = err.get("msg", "")
    payload = build_error_response(
        code="UNPROCESSABLE",
        message="Request validation failed",
        status_code=422,
        request_id=_correlation_id(request),
        details=fields,
    )
    return _emit_correlation_id(request, JSONResponse(status_code=422, content=payload))


async def not_found_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Route-not-found also uses the envelope.

    Starlette emits a plain 404 body; without this handler the shape of an
    error depends on which code path produced it, so a client cannot branch
    the same way in both cases.
    """
    if exc.status_code == 404 and exc.detail is not None and exc.detail == "Not Found":
        payload = build_error_response(
            code="NOT_FOUND",
            message=f"No route for {request.method} {request.url.path}",
            status_code=404,
            request_id=_correlation_id(request),
        )
        return _emit_correlation_id(request, JSONResponse(status_code=404, content=payload))
    return await http_exception_handler(request, exc)


def register_error_handlers(app) -> None:
    """Register every handler that produces the standard error envelope.

    Order matters: FastAPI matches the most specific exception first, so the
    validation handler must be registered before the generic HTTP handler.
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, not_found_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
