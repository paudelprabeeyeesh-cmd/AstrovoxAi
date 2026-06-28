"""Shared authentication helpers for FastAPI routers."""

from fastapi import HTTPException, status

from .supabase_client import get_supabase


def get_user_id_from_token(authorization: str) -> str:
    """Validate a Bearer token via Supabase and return the user id."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    try:
        token = authorization.replace("Bearer ", "")
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
