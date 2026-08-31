"""API versioning and request validation."""

import time
import logging
from typing import Optional
from functools import wraps

from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


API_VERSIONS = {
    "v1": {"status": "stable", "deprecated": False},
    "v2": {"status": "current", "deprecated": False},
}

CURRENT_API_VERSION = "v2"
MINIMUM_API_VERSION = "v1"


def require_api_version(min_version: str = "v1"):
    """Decorator to require a minimum API version."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request:
                version = request.headers.get("X-API-Version", CURRENT_API_VERSION)
                if version < min_version:
                    raise HTTPException(
                        status_code=status.HTTP_426_UPGRADE_REQUIRED,
                        detail=f"API version {version} is not supported. Minimum: {min_version}",
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class APIVersionMiddleware:
    """Add API version headers to responses."""

    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        response.headers["X-API-Version"] = CURRENT_API_VERSION
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response
