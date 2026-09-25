from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.utils.auth.auth_utils import get_user_id_from_token

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
    return get_user_id_from_token(authorization)


async def require_admin(
    request: Request,
    authorization: str = None,
) -> str:
    user_id = await require_verified_email(request, authorization)
    return user_id


__all__ = ["require_verified_email", "require_admin"]
