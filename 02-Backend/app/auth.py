import os

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address

from .supabase_client import get_supabase

supabase = get_supabase()
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["authentication"])


# Pydantic models
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


# Routes
@router.post("/signup")
@limiter.limit("5/minute")
async def sign_up(request: SignUpRequest):
    """Register a new user with Supabase Auth"""
    try:
        response = supabase.auth.sign_up(
            {
                "email": request.email,
                "password": request.password,
                "options": {
                    "data": {
                        "full_name": request.full_name,
                        "username": request.email.split("@")[0],
                    }
                },
            }
        )

        return {
            "status": "OK",
            "message": "User registered successfully. Please verify your email.",
            "user": {
                "id": response.user.id if response.user else None,
                "email": response.user.email if response.user else None,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: LoginRequest):
    """Login user with email and password"""
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )


@router.post("/logout")
async def logout():
    """Logout user (client-side operation in Supabase)"""
    return {
        "status": "OK",
        "message": "Logout successful. Please clear your session tokens on the client.",
    }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Send password reset email"""
    try:
        supabase.auth.reset_password_for_email(
            request.email,
            options={
                "redirect_to": f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/reset-password"
            },
        )

        return {"status": "OK", "message": "Password reset email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me")
async def get_current_user(authorization: str = None):
    """Get current authenticated user (requires token in header)"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    try:
        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "")

        # Get user from token
        response = supabase.auth.get_user(token)

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Fetch user profile
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh token"
        )
