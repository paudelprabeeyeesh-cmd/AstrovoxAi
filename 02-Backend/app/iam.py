"""
Authentication dependencies for FastAPI endpoints.

Replaces the legacy `":admin" in authorization` hack with proper
JWT-based role verification and ownership checks.

Usage:
    @router.get("/admin/users")
    async def list_users(principal: Principal = Depends(require_admin)):
        ...

    @router.delete("/conversations/{conv_id}")
    async def delete_conversation(
        conv_id: str,
        principal: Principal = Depends(get_current_principal),
    ):
        # verify ownership before proceeding
        ...
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Request

from .security_hardening import (
    JWTError,
    Principal,
    is_admin_role,
    jwt_decode,
    principal_from_jwt_claims,
)


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        # Development fallback. In production this must be set.
        import secrets

        secret = secrets.token_urlsafe(32)
    return secret


def get_jwt_algorithms() -> List[str]:
    raw = os.getenv("JWT_ALGORITHMS", "HS256")
    return [a.strip() for a in raw.split(",") if a.strip()]


def _extract_bearer_token(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    # Fall back to X-API-Key for service accounts
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key
    return None


async def get_current_principal(
    request: Request,
) -> Principal:
    """Resolve the calling principal from the request.

    Returns an anonymous principal if no credentials are supplied.
    Raises 401 for invalid tokens.
    """
    token = _extract_bearer_token(request)
    if not token:
        return Principal(
            id="anonymous",
            email="",
            role="anonymous",
            authenticated_via="anon",
        )
    try:
        claims = jwt_decode(
            token,
            secret=get_jwt_secret(),
            algorithms=get_jwt_algorithms(),
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}")

    return principal_from_jwt_claims(claims)


async def require_authenticated(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if principal.role == "anonymous":
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


async def require_admin(
    principal: Principal = Depends(require_authenticated),
) -> Principal:
    if not is_admin_role(principal.role):
        raise HTTPException(
            status_code=403,
            detail="admin role required",
        )
    return principal


async def require_scope(scope: str):
    """Factory for scope-checking dependencies."""

    async def _checker(
        principal: Principal = Depends(require_authenticated),
    ) -> Principal:
        if not principal.has_scope(scope) and not principal.is_admin():
            raise HTTPException(
                status_code=403,
                detail=f"scope '{scope}' required",
            )
        return principal

    return _checker


def require_ownership(resource_owner_id: Optional[str]):
    """Factory for ownership-checking dependencies."""

    async def _checker(
        principal: Principal = Depends(require_authenticated),
    ) -> Principal:
        if principal.is_admin():
            return principal
        if resource_owner_id is None or str(principal.id) != str(
            resource_owner_id
        ):
            raise HTTPException(
                status_code=403,
                detail="resource access denied",
            )
        return principal

    return _checker
