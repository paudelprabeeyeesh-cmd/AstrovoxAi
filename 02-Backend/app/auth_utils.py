"""Shared authentication helpers for FastAPI routers."""

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .supabase_client import get_supabase


security_scheme = HTTPBearer(auto_error=False)


def get_user_id_from_token(authorization: str) -> str:
    """Validate a Bearer token via Supabase and return the user id."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    try:
        token = authorization.replace("Bearer ", "", 1).strip()
        response = get_supabase().auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if not response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return str(response.user.id)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Dict[str, Any]:
    """FastAPI dependency that resolves the authenticated user.

    Returns the authenticated user or raises 401 when credentials are
    provided but invalid. Endpoints that allow anonymous access should
    use a separate optional-auth dependency.
    """

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    token = credentials.credentials
    try:
        response = get_supabase().auth.get_user(token)
        if response and getattr(response, "user", None):
            user = response.user
            return {
                "id": str(getattr(user, "id", "anonymous")),
                "email": getattr(user, "email", ""),
                "role": getattr(user, "role", "user"),
            }
    except Exception:
        logger.warning("supabase auth verification failed", exc_info=True)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
