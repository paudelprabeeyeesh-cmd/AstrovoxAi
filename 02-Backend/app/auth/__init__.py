from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.utils.auth.auth_utils import get_user_id_from_token, get_current_user

security_scheme = HTTPBearer(auto_error=False)


async def require_verified_email(
    request: Request,
    authorization: str = None,
) -> str:
    if not authorization:
        authorization = ""
    if hasattr(request, "headers"):
        auth_header = request.headers.get("authorization", authorization or "")
        if not authorization:
            authorization = auth_header
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def require_admin(
    request: Request,
    authorization: str = None,
) -> str:
    user_id = await require_verified_email(request, authorization)
    return user_id


async def get_principal(
    request: Request,
) -> Any:
    authorization = request.headers.get("authorization", "")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


__all__ = [
    "require_verified_email",
    "require_admin",
    "get_current_user",
    "get_principal",
]
