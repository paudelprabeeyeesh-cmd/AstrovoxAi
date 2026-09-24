import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from .supabase_client import get_supabase
from .services.auth_service import check_login_lockout, record_login_attempt
from .services.mfa_service import is_mfa_enabled, verify_mfa
from .services.session_service import create_session, delete_session, get_session, refresh_session as refresh_session_service
from .services.magic_link_service import create_magic_link, verify_magic_link
from .services.oauth_service import get_oauth_url

supabase = get_supabase()
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["authentication"])


class RoleResponse(BaseModel):
    role: str


class UserRolesResponse(BaseModel):
    user_id: str
    roles: List[str]


def get_user_id_from_token_with_roles(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    try:
        token = authorization.replace("Bearer ", "")
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        user = response.user
        roles: List[str] = []
        app_metadata = getattr(user, "app_metadata", {}) or {}
        raw_roles = app_metadata.get("roles", [])
        if isinstance(raw_roles, list):
            roles = [str(r) for r in raw_roles]
        elif isinstance(raw_roles, str):
            roles = [raw_roles]
        return {"user_id": user.id, "roles": roles}
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def role_required(role: str):
    def _dependency(authorization: Optional[str] = Header(None)):
        info = get_user_id_from_token_with_roles(authorization)
        if role not in info["roles"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return info["user_id"]
    return _dependency


require_admin = role_required("admin")


def require_verified_email(authorization: Optional[str] = Header(None)):
    info = get_user_id_from_token_with_roles(authorization)
    return info["user_id"]


def get_current_user(authorization: Optional[str] = Header(None)):
    info = get_user_id_from_token_with_roles(authorization)
    return info["user_id"]


class SignUpRequest(BaseModel):
    email: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ResetPasswordRequest(BaseModel):
    email: str


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class OAuthRequest(BaseModel):
    provider: str
    access_token: str
    email: Optional[str] = None


@router.post("/signup")
@limiter.limit("5/minute")
async def sign_up(request: Request, body: SignUpRequest):
    from app.services.auth_service import create_user, get_user_by_email
    from app.services.magic_link_service import create_magic_link
    existing = get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = create_user(body.email, body.password, body.full_name)
    token = str(uuid.uuid4()) + str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    from app.services.auth_service import create_email_verification_token
    create_email_verification_token(user["id"], token, expires_at)
    magic_link = create_magic_link(user["id"], user["email"], expires_in_minutes=1440)
    return {
        "status": "OK",
        "message": "User registered successfully. Please verify your email.",
        "user": {
            "id": user["id"],
            "email": user["email"],
        },
        "verification_token": token,
        "magic_link_token": magic_link["token"],
    }


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    client_ip = request.client.host if request.client else "unknown"
    lockout = check_login_lockout(client_ip)
    if lockout:
        raise HTTPException(status_code=429, detail=lockout)

    from app.services.auth_service import get_user_by_email, verify_password
    user = get_user_by_email(body.email)
    if not user or not verify_password(user, body.password):
        record_login_attempt(client_ip, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    record_login_attempt(client_ip, success=True)

    if is_mfa_enabled(user["id"]):
        return {
            "status": "OK",
            "message": "MFA required",
            "user": {"id": user["id"], "email": user["email"]},
            "mfa_required": True,
        }

    session = create_session(user["id"], ip_address=client_ip)
    return {
        "status": "OK",
        "message": "Login successful",
        "user": {"id": user["id"], "email": user["email"]},
        "session": {
            "access_token": session["session_token"],
            "refresh_token": session["refresh_token"],
            "expires_at": session["expires_at"],
        },
    }


@router.post("/logout")
async def logout():
    return {
        "status": "OK",
        "message": "Logout successful. Please clear your session tokens on the client.",
    }


@router.post("/reset-password")
async def reset_password(request: Request, body: ResetPasswordRequest):
    from app.services.auth_service import get_user_by_email, create_password_reset_token
    user = get_user_by_email(body.email)
    if user:
        token = str(uuid.uuid4()) + str(uuid.uuid4())
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        create_password_reset_token(user["id"], token, expires_at)
    return {"status": "OK", "message": "Password reset email sent successfully"}


@router.get("/me")
async def get_current_user(authorization: str = None):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    try:
        token = authorization.replace("Bearer ", "")
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        profile_response = (
            supabase.table("profiles").select("*").eq("id", response.user.id).execute()
        )
        profile = profile_response.data[0] if profile_response.data else None
        return {
            "status": "OK",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "profile": profile,
            },
        }
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


@router.get("/me/roles", response_model=UserRolesResponse)
async def get_current_user_roles(authorization: Optional[str] = None):
    info = get_user_id_from_token_with_roles(authorization)
    return UserRolesResponse(user_id=info["user_id"], roles=info["roles"])


@router.post("/oauth")
async def oauth_login(request: OAuthRequest):
    try:
        response = supabase.auth.sign_in_with_otp(
            {"email": request.email or "", "create_user": True}
        )
        return {
            "status": "OK",
            "provider": request.provider,
            "message": "OAuth flow initiated",
            "otp_sent": bool(response),
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    try:
        response = supabase.auth.refresh_session(refresh_token)
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        return {
            "status": "OK",
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
            },
        }
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh token"
        )


from uuid import uuid4
from datetime import timedelta
