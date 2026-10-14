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

GENERIC_SERVER_ERROR = "An internal error occurred. Please retry; if it persists, contact support with the request id."

# Shapes that mean a detail string is an exception's repr rather than a
# message a human wrote for the client. A `str(exc)` interpolates the
# exception class name, a traceback's file path, or a SQLAlchemy/sqlite phrase,
# any of which discloses internals about the deployment.
_RAW_EXCEPTION_MARKERS = (
    "Traceback (most recent call last)",
    "File \"",
    "sqlalchemy.",
    "sqlite3.",
    "psycopg",
    "OperationalError",
    "IntegrityError",
    "ProgrammingError",
    "NameError",
    "AttributeError",
    "KeyError",
    "TypeError",
    "ValueError",
    "RuntimeError",
    # Driver messages that a `str(exc)` interpolation passes through verbatim.
    "no such table",
    "no such column",
    "UNIQUE constraint failed",
    "database is locked",
    "syntax error at or near",
)


def _looks_like_raw_exception(detail: object) -> bool:
    if not isinstance(detail, str) or not detail:
        return False
    return any(marker in detail for marker in _RAW_EXCEPTION_MARKERS) or (
        "(" in detail and ")" in detail and detail.split("(")[0].replace(".", "").isidentifier()
    )


def _sanitize_server_error(request: Request, detail: object):
    """Return a safe client message for a 5xx, logging the real one.

    Route handlers interpolate `str(exc)` into `detail=` for 5xx responses,
    which puts database paths, SQL fragments and exception class names in the
    response body. The client gets a generic message and the correlation id;
    the real cause goes to the log with the same id so it can be correlated.
    """
    if _looks_like_raw_exception(detail):
        logger.error(
            "Suppressed internal error detail for %s %s (correlation_id=%s): %s",
            request.method,
            request.url.path,
            _correlation_id(request),
            detail,
            exc_info=True,
        )
        return GENERIC_SERVER_ERROR
    return detail


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
    # A 5xx detail that came from `str(exc)` discloses internals, so it is
    # replaced. Every route that interpolates an exception is covered at once
    # rather than needing 344 separate edits.
    detail = exc.detail
    if exc.status_code >= 500:
        detail = _sanitize_server_error(request, exc.detail)
    payload = build_error_response(
        code=code,
        message=str(detail),
        status_code=exc.status_code,
        request_id=_correlation_id(request),
    )
    return _emit_correlation_id(request, JSONResponse(status_code=exc.status_code, content=payload))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    payload = build_error_response(
        code="INTERNAL_ERROR",
        message=GENERIC_SERVER_ERROR,
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
