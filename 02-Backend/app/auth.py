import os
<<<<<<< HEAD
import logging
import time

from fastapi import APIRouter, HTTPException, status, Header, Request
from pydantic import BaseModel, EmailStr, field_validator
=======
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
from slowapi import Limiter
from slowapi.util import get_remote_address

from .supabase_client import get_supabase
<<<<<<< HEAD
from app.middleware.security.security_hardening import get_audit_log
from .security.brute_force_protection import brute_force_protection
from .security.password_strength import password_enforcer
from .security.token_revocation import token_revocation_list
from .security.refresh_token_rotation import refresh_token_rotation
from .security.anomaly_alerts import auth_anomaly_detector, AuthEvent
from .security.security_webhook import security_event_webhook
from app.utils.auth.auth_utils import get_user_id_from_token
=======
from .services.auth_service import check_login_lockout, record_login_attempt
from .services.mfa_service import is_mfa_enabled, verify_mfa
from .services.session_service import create_session, delete_session, get_session, refresh_session as refresh_session_service
from .services.magic_link_service import create_magic_link, verify_magic_link
from .services.oauth_service import get_oauth_url
>>>>>>> 10617909505295e4a37b817bb54db2364934b978

logger = logging.getLogger(__name__)
supabase = get_supabase()
_audit = get_audit_log()
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["authentication"])


<<<<<<< HEAD
async def require_verified_email(request: Request, authorization: str = Header(None)) -> str:
    if not authorization:
        authorization = request.headers.get("authorization", "")
    return get_user_id_from_token(authorization)


async def require_admin(request: Request, authorization: str = Header(None)) -> str:
    return await require_verified_email(request, authorization)


def _dispatch_security_event(event_type: str, user_id: str, description: str, severity: str = "medium", metadata: Optional[dict] = None) -> None:
    if security_event_webhook is None:
        return
    security_event_webhook.dispatch(SecurityEvent(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        description=description,
        timestamp=time.time(),
        metadata=metadata or {},
    ))


class SecurityEvent:
    def __init__(self, event_type: str, severity: str, user_id: str, description: str, timestamp: float, metadata: dict):
        self.event_type = event_type
        self.severity = severity
        self.user_id = user_id
        self.description = description
        self.timestamp = timestamp
        self.metadata = metadata


# Pydantic models
=======
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


>>>>>>> 10617909505295e4a37b817bb54db2364934b978
class SignUpRequest(BaseModel):
    email: str
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        result = password_enforcer.validate(v)
        if not result.valid:
            raise ValueError("; ".join(result.feedback))
        return v


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
<<<<<<< HEAD
    """Register a new user with Supabase Auth"""
    try:
        response = supabase.auth.sign_up(
            {
                "email": body.email,
                "password": body.password,
                "options": {
                    "data": {
                        "full_name": body.full_name,
                        "username": body.email.split("@")[0],
                    }
                },
            }
        )

        _audit.record(
            actor=body.email,
            action="auth_signup",
            target="user",
            outcome="success",
        )
        return {
            "status": "OK",
            "message": "Signup successful",
            "user": {"id": response.user.id, "email": response.user.email},
            "session": {
                "access_token": (
                    response.session.access_token if response.session else None
                ),
                "refresh_token": (
                    response.session.refresh_token if response.session else None
                ),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        _audit.record(
            actor=body.email,
            action="auth_signup",
            target="user",
            outcome="failed",
            metadata={"error": str(e)[:100]},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Signup failed"
        )
=======
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
>>>>>>> 10617909505295e4a37b817bb54db2364934b978


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
<<<<<<< HEAD
    """Login user with email and password"""
    client_ip = request.client.host if request.client else "unknown"

    is_locked, remaining = brute_force_protection.is_locked(body.email)
    if is_locked:
        _audit.record(
            actor=body.email,
            action="auth_login",
            target="user",
            outcome="failed",
            metadata={"reason": "locked_out", "remaining_seconds": int(remaining) if remaining else 0},
        )
        _dispatch_security_event(
            "auth_locked_out", body.email,
            f"Login attempt on locked account from {client_ip}",
            severity="high",
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account temporarily locked. Try again in {int(remaining) if remaining else 0} seconds.",
        )

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )

        if not response.user:
            brute_force_protection.record_failure(body.email)
            remaining_attempts = brute_force_protection.remaining_attempts(body.email)
            _audit.record(
                actor=body.email,
                action="auth_login",
                target="user",
                outcome="failed",
                metadata={"reason": "invalid_credentials", "remaining_attempts": remaining_attempts},
            )
            auth_anomaly_detector.record(AuthEvent(
                user_id=body.email, ip=client_ip, country=None,
                user_agent=request.headers.get("user-agent", ""), timestamp=time.time(),
            ))
            _dispatch_security_event(
                "auth_failed", body.email,
                f"Failed login from {client_ip}",
                severity="medium",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid credentials. {remaining_attempts} attempts remaining before lockout.",
            )

        brute_force_protection.record_success(body.email)
        _audit.record(
            actor=body.email,
            action="auth_login",
            target="user",
            outcome="success",
        )
        auth_anomaly_detector.record(AuthEvent(
            user_id=str(response.user.id), ip=client_ip, country=None,
            user_agent=request.headers.get("user-agent", ""), timestamp=time.time(),
        ))
        return {
            "status": "OK",
            "message": "Login successful",
            "user": {"id": response.user.id, "email": response.user.email},
            "session": {
                "access_token": (
                    response.session.access_token if response.session else None
                ),
                "refresh_token": (
                    response.session.refresh_token if response.session else None
                ),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        brute_force_protection.record_failure(body.email)
        _audit.record(
            actor=body.email,
            action="auth_login",
            target="user",
            outcome="failed",
            metadata={"error": str(e)[:100]},
        )
        _dispatch_security_event(
            "auth_error", body.email,
            f"Login error from {client_ip}: {str(e)[:100]}",
            severity="high",
        )
=======
    client_ip = request.client.host if request.client else "unknown"
    lockout = check_login_lockout(client_ip)
    if lockout:
        raise HTTPException(status_code=429, detail=lockout)

    from app.services.auth_service import get_user_by_email, verify_password
    user = get_user_by_email(body.email)
    if not user or not verify_password(user, body.password):
        record_login_attempt(client_ip, success=False)
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
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
<<<<<<< HEAD
async def logout(request: Request, authorization: str = Header(None)):
    """Logout user and revoke tokens"""
    user_id = "anonymous"
    if authorization:
        token = authorization.replace("Bearer ", "", 1).strip()
        jti = token[:32]
        token_revocation_list.revoke(jti, user_id, time.time() + 3600, reason="logout")
        refresh_token_rotation.revoke_all(user_id)
        try:
            user_resp = supabase.auth.get_user(token)
            if user_resp.user:
                user_id = str(user_resp.user.id)
        except Exception:
            pass
    _audit.record(actor=user_id, action="auth_logout", target="user", outcome="success")
    _dispatch_security_event("auth_logout", user_id, "User logged out", severity="low")
=======
async def logout():
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
    return {
        "status": "OK",
        "message": "Logout successful. Tokens revoked. Please clear your session tokens on the client.",
    }


@router.post("/reset-password")
async def reset_password(request: Request, body: ResetPasswordRequest):
<<<<<<< HEAD
    """Send password reset email with rate limiting"""
    from .security.secure_password_reset import secure_password_reset
    try:
        raw_token = secure_password_reset.create_token(body.email)
        supabase.auth.reset_password_for_email(
            body.email,
            options={
                "redirect_to": f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/reset-password",
            },
        )
        _audit.record(
            actor=body.email,
            action="auth_password_reset",
            target="user",
            outcome="success",
        )
        return {"status": "OK", "message": "Password reset email sent successfully"}
    except Exception as e:
        _audit.record(
            actor=body.email,
            action="auth_password_reset",
            target="user",
            outcome="failed",
            metadata={"error": str(e)[:100]},
        )
        logger.warning(f"Password reset failed: {str(e)[:100]}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset failed")
=======
    from app.services.auth_service import get_user_by_email, create_password_reset_token
    user = get_user_by_email(body.email)
    if user:
        token = str(uuid.uuid4()) + str(uuid.uuid4())
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        create_password_reset_token(user["id"], token, expires_at)
    return {"status": "OK", "message": "Password reset email sent successfully"}
>>>>>>> 10617909505295e4a37b817bb54db2364934b978


@router.get("/me")
async def get_current_user(authorization: str = None):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    try:
        token = authorization.replace("Bearer ", "")
<<<<<<< HEAD

=======
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
        response = supabase.auth.get_user(token)
        if not response.user:
            _audit.record(
                actor="anonymous",
                action="auth_get_me",
                target="user",
                outcome="failed",
                metadata={"reason": "invalid_token"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
<<<<<<< HEAD

        _audit.record(
            actor=response.user.id,
            action="auth_get_me",
            target="user",
            outcome="success",
        )
=======
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
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
<<<<<<< HEAD
    except Exception:
        _audit.record(
            actor="anonymous",
            action="auth_get_me",
            target="user",
            outcome="failed",
        )
=======
    except Exception:  # noqa: BLE001
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


<<<<<<< HEAD
@router.post("/refresh")
async def refresh_token(request: Request, refresh_token: str):
    """Refresh access token with rotation and reuse detection"""
=======
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
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
    try:
        response = supabase.auth.refresh_session(refresh_token)
        if not response.session:
            _audit.record(
                actor="anonymous",
                action="auth_refresh",
                target="session",
                outcome="failed",
                metadata={"reason": "invalid_refresh_token"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
<<<<<<< HEAD

        user_id = str(response.user.id) if response.user else "anonymous"
        try:
            new_refresh_token, rotated = refresh_token_rotation.rotate(refresh_token, user_id)
        except ValueError:
            _audit.record(
                actor=user_id,
                action="auth_refresh",
                target="session",
                outcome="failed",
                metadata={"reason": "refresh_token_reuse"},
            )
            _dispatch_security_event(
                "refresh_token_reuse", user_id,
                "Refresh token reuse detected - sessions revoked",
                severity="critical",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected"
            )

        _audit.record(
            actor=user_id,
            action="auth_refresh",
            target="session",
            outcome="success",
        )
=======
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
        return {
            "status": "OK",
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": new_refresh_token,
            },
        }
    except HTTPException:
        raise
<<<<<<< HEAD
    except Exception:
        _audit.record(
            actor="anonymous",
            action="auth_refresh",
            target="session",
            outcome="failed",
        )
=======
    except Exception:  # noqa: BLE001
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh token"
        )

<<<<<<< HEAD
=======

from uuid import uuid4
from datetime import timedelta
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
