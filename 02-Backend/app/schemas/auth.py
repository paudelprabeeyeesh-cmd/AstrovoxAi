from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    device_name: Optional[str] = Field(None, max_length=200)
    device_type: Optional[str] = Field(None, max_length=50)
    platform: Optional[str] = Field(None, max_length=100)
    browser: Optional[str] = Field(None, max_length=100)
    fingerprint: Optional[str] = Field(None, max_length=200)
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=8)


class LogoutRequest(BaseModel):
    session_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class EmailVerificationRequest(BaseModel):
    token: str = Field(..., min_length=1)


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkVerifyRequest(BaseModel):
    token: str = Field(..., min_length=1)


class MFASetupRequest(BaseModel):
    pass


class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)
    backup_code: Optional[str] = Field(None, min_length=8, max_length=8)


class MFADisableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class DeviceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    device_type: str = Field("unknown", max_length=50)
    platform: Optional[str] = Field(None, max_length=100)
    browser: Optional[str] = Field(None, max_length=100)
    fingerprint: str = Field(..., min_length=1, max_length=200)


class DeviceTrustRequest(BaseModel):
    device_id: str = Field(..., min_length=1)


class OAuthLoginRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=50)
    access_token: str = Field(..., min_length=1)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=200)


class OAuthCallbackRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1)
    state: Optional[str] = None


class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    scopes: str = Field("read", max_length=500)


class APIKeyRevokeRequest(BaseModel):
    key_id: str = Field(..., min_length=1)


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class PermissionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class RolePermissionAssignRequest(BaseModel):
    role_id: str = Field(..., min_length=1)
    permission_id: str = Field(..., min_length=1)


class UserRoleAssignRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    role_id: str = Field(..., min_length=1)


class AuthResponse(BaseModel):
    status: str = "OK"
    message: str
    user: Optional[dict] = None
    session: Optional[dict] = None
    mfa_required: bool = False
    mfa_secret: Optional[str] = None
    mfa_backup_codes: Optional[List[str]] = None


class SessionInfo(BaseModel):
    id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    last_activity_at: datetime
    created_at: datetime
    is_current: bool = False


class DeviceInfo(BaseModel):
    id: str
    name: str
    device_type: str
    platform: Optional[str]
    browser: Optional[str]
    trusted: bool
    last_seen_at: datetime
    created_at: datetime


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    email_verified: bool
    role: str
    plan: str
    mfa_enabled: bool
    created_at: datetime


class RoleInfo(BaseModel):
    id: str
    name: str
    description: Optional[str]
    permissions: List[str] = []


class PermissionInfo(BaseModel):
    id: str
    name: str
    description: Optional[str]


class APIKeyInfo(BaseModel):
    id: str
    name: str
    key: Optional[str] = None
    scopes: str
    last_used: Optional[datetime]
    created_at: datetime
