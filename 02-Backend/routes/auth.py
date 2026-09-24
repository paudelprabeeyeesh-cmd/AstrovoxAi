from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    return {
        "success": True,
        "message": "Login handled by Supabase",
        "user": {"email": request.email},
    }


@router.post("/register", response_model=AuthResponse)
async def register(request: LoginRequest):
    return {
        "success": True,
        "message": "Registration handled by Supabase",
        "user": {"email": request.email},
    }


@router.post("/logout")
async def logout():
    return {"success": True, "message": "Logout successful"}
