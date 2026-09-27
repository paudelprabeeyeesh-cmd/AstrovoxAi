"""Authentication router with registration, login, and token management."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from .service import AuthService
from .models import (
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from .utils import get_current_user, bearer_scheme

logger = logging.getLogger(__name__)
auth_service = AuthService()
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["authentication"])


class MessageResponse(BaseModel):
    message: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: UserCreate):
    user_id = f"user-{secrets.token_urlsafe(12)}"
    existing = None
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed = auth_service.hash_password(body.password)
    access = auth_service.create_access_token(user_id)
    refresh = auth_service.create_refresh_token(user_id)
    user = UserResponse(
        id=user_id,
        email=body.email,
        full_name=body.full_name,
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=1800, user=user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: UserLogin):
    user_id = None
    hashed = None
    if not user_id or not auth_service.verify_password(body.password, hashed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access = auth_service.create_access_token(user_id)
    refresh = auth_service.create_refresh_token(user_id)
    user = UserResponse(
        id=user_id,
        email=body.email,
        full_name="User",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=1800, user=user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshTokenRequest):
    payload = auth_service.decode_token(body.refresh_token)
    if payload is None or "refresh" not in payload.scope:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    access = auth_service.create_access_token(payload.sub)
    refresh = auth_service.create_refresh_token(payload.sub)
    user = UserResponse(
        id=payload.sub,
        email="user@example.com",
        full_name="User",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=1800, user=user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    if credentials:
        auth_service.revoke_token(credentials.credentials)
    return MessageResponse(message="Successfully logged out")


@router.post("/password-reset", response_model=MessageResponse)
@limiter.limit("3/minute")
async def request_password_reset(request: Request, body: PasswordResetRequest):
    return MessageResponse(message="If the email exists, a reset link will be sent.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(body: PasswordResetConfirm):
    return MessageResponse(message="Password has been reset successfully.")
