import os
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status, Header, Request
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from typing import Optional

from app.repositories.database.client import get_db
from app.middleware.security.security_hardening import get_audit_log
from app.utils.auth.auth_utils import get_user_id_from_token

logger = logging.getLogger(__name__)
_audit = get_audit_log()
limiter = Limiter(key_func=get_remote_address)

try:
    from app.supabase_client import get_supabase
    supabase = get_supabase()
except Exception:
    supabase = None

router = APIRouter(prefix="/auth", tags=["authentication"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _ensure_lockout_table(conn) -> None:
    """Ensure the login_attempts table matches the shared schema.

    The table has no init path and two modules used to create it with
    different column sets, so whichever ran first won and the other failed
    at query time. The schema now lives in one place.
    """
    from app.services.login_attempt_schema import ensure_login_attempts_table

    ensure_login_attempts_table(conn)


def _check_brute_force(ip: str, email: str) -> None:
    """Raise 429 when the lockout threshold is reached.

    SQLAlchemy 2.x refuses a plain string in ``Session.execute``; raw SQL
    must be wrapped in ``text()``. Without it this raises
    ``ArgumentError: Textual SQL expression ... should be explicitly
    declared as text(...)`` and the lockout silently never applies, which
    is a missing security control rather than a visible failure.
    """
    with get_db() as conn:
        _ensure_lockout_table(conn)
        conn.commit()
        cutoff = (datetime.utcnow() - timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
        row = conn.execute(
            text(
                """
            SELECT COUNT(*) AS failed_count, MAX(created_at) AS last_attempt
            FROM login_attempts
            WHERE ip = :ip AND email = :email AND success = 0 AND created_at > :cutoff
            """
            ),
            {"ip": ip, "email": email, "cutoff": cutoff},
        ).mappings().fetchone()
        # .mappings() gives key access; a bare Row does not support
        # row["failed_count"] for an aggregate SELECT.
        if row and row["failed_count"] >= MAX_FAILED_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {LOCKOUT_MINUTES} minutes.",
            )


def _record_login_attempt(ip: str, email: str, success: bool) -> None:
    """Record one login attempt for the lockout window."""
    with get_db() as conn:
        _ensure_lockout_table(conn)
        conn.execute(
            text(
                "INSERT INTO login_attempts (id, ip, email, success, created_at) "
                "VALUES (:id, :ip, :email, :success, :created_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "ip": ip,
                "email": email,
                "success": 1 if success else 0,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        conn.commit()


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr


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
    if supabase is None:
        raise HTTPException(status_code=500, detail="Auth not configured")
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


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    if supabase is None:
        raise HTTPException(status_code=500, detail="Auth not configured")

    client_ip = request.client.host if request.client else "unknown"
    _check_brute_force(client_ip, body.email)

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )

        if not response.user:
            _audit.record(
                actor=body.email,
                action="auth_login",
                target="user",
                outcome="failed",
                metadata={"reason": "invalid_credentials", "ip": client_ip},
            )
            _record_login_attempt(client_ip, body.email, False)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        _audit.record(
            actor=response.user.id,
            action="auth_login",
            target="user",
            outcome="success",
            metadata={"ip": client_ip},
        )
        _record_login_attempt(client_ip, body.email, True)
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
        _audit.record(
            actor=body.email,
            action="auth_login",
            target="user",
            outcome="failed",
            metadata={"error": str(e)[:100], "ip": client_ip},
        )
        _record_login_attempt(client_ip, body.email, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )


@router.post("/logout")
async def logout(authorization: str = Header(None)):
    if supabase is None:
        raise HTTPException(status_code=500, detail="Auth not configured")
    user_id = get_user_id_from_token(authorization) if authorization else "anonymous"
    _audit.record(actor=user_id, action="auth_logout", target="user", outcome="success")
    return {
        "status": "OK",
        "message": "Logout successful. Please clear your session tokens on the client.",
    }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    if supabase is None:
        raise HTTPException(status_code=500, detail="Auth not configured")
    try:
        supabase.auth.reset_password_for_email(
            request.email,
            options={
                "redirect_to": f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/reset-password"
            },
        )
        _audit.record(
            actor=request.email,
            action="auth_password_reset",
            target="user",
            outcome="success",
        )
        return {"status": "OK", "message": "Password reset email sent successfully"}
    except Exception as e:
        _audit.record(
            actor=request.email,
            action="auth_password_reset",
            target="user",
            outcome="failed",
            metadata={"error": str(e)[:100]},
        )
        logger.warning(f"Password reset failed: {str(e)[:100]}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset failed")


@router.get("/me")
async def get_current_user(authorization: str = None):
    if supabase is None:
        raise HTTPException(status_code=500, detail="Auth not configured")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    try:
        token = authorization.replace("Bearer ", "")
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

        _audit.record(
            actor=response.user.id,
            action="auth_get_me",
            target="user",
            outcome="success",
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
    except Exception:
        _audit.record(
            actor="anonymous",
            action="auth_get_me",
            target="user",
            outcome="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    if supabase is None:
        raise HTTPException(status_code=500, detail="Auth not configured")
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

        _audit.record(
            actor=response.user.id if response.user else "anonymous",
            action="auth_refresh",
            target="session",
            outcome="success",
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
    except Exception:
        _audit.record(
            actor="anonymous",
            action="auth_refresh",
            target="session",
            outcome="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh token"
        )
