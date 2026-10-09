"""Comprehensive authentication router."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.schemas.auth import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyRevokeRequest,
    AuthResponse,
    ChangePasswordRequest,
    DeviceCreateRequest,
    DeviceInfo,
    DeviceTrustRequest,
    EmailVerificationRequest,
    LoginRequest,
    LogoutRequest,
    MFADisableRequest,
    MFAVerifyRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    OAuthCallbackRequest,
    OAuthLoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    RefreshTokenRequest,
    RoleInfo,
    SessionInfo,
    UserInfo,
)
from app.services.auth_service import create_user, get_user_by_email, verify_password
from app.services.session_service import (
    create_session,
    delete_all_user_sessions,
    delete_session,
    get_session,
    get_user_sessions,
    refresh_session,
    update_session_activity,
)
from app.services.mfa_service import (
    generate_backup_codes,
    get_mfa_secret,
    is_mfa_enabled,
    setup_mfa,
    verify_mfa,
)
from app.services.device_service import (
    create_device,
    delete_device,
    get_device,
    get_devices,
    trust_device,
)
from app.services.magic_link_service import create_magic_link, verify_magic_link
from app.services.oauth_service import get_or_create_oauth_user, get_oauth_url
from app.rbac import get_user_role, has_permission, require_permission, role_required
from app.api_keys import create_api_key, list_api_keys, revoke_api_key

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_token_from_header(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization.replace("Bearer ", "")


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    existing = get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = create_user(request.email, request.password, request.full_name)
    return AuthResponse(
        status="OK",
        message="User registered successfully. Please verify your email.",
        user={"id": user["id"], "email": user["email"]},
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: Request, body: LoginRequest):
    client_ip = request.client.host if request.client else "unknown"
    lockout = None  # check_login_lockout(client_ip)
    if lockout:
        raise HTTPException(status_code=429, detail=lockout)

    user = get_user_by_email(body.email)
    if not user or not verify_password(user, body.password):
        record_login_attempt(client_ip, success=False)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if is_mfa_enabled(user["id"]):
        return AuthResponse(
            status="OK",
            message="MFA required",
            user={"id": user["id"], "email": user["email"]},
            mfa_required=True,
        )

    session = create_session(
        user["id"],
        ip_address=client_ip,
        user_agent=body.fingerprint,
    )
    if body.fingerprint:
        device = get_device_by_fingerprint(body.fingerprint)
        if not device:
            create_device(
                user["id"],
                name=body.device_name or "Unknown Device",
                fingerprint=body.fingerprint,
                device_type=body.device_type or "unknown",
                platform=body.platform,
                browser=body.browser,
            )

    return AuthResponse(
        status="OK",
        message="Login successful",
        user={"id": user["id"], "email": user["email"], "role": user["role"], "email_verified": bool(user["email_verified"])},
        session={
            "access_token": session["session_token"],
            "refresh_token": session["refresh_token"],
            "expires_at": session["expires_at"],
        },
    )


@router.post("/login/mfa", response_model=AuthResponse)
async def login_mfa(request: Request, body: MFAVerifyRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = get_user_by_id(session["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not verify_mfa(user["id"], body.code, body.backup_code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    update_session_activity(token)
    return AuthResponse(
        status="OK",
        message="Login successful",
        user={"id": user["id"], "email": user["email"], "role": user["role"]},
        session={
            "access_token": session["session_token"],
            "refresh_token": session["refresh_token"],
            "expires_at": session["expires_at"],
        },
    )


@router.post("/logout", response_model=AuthResponse)
async def logout(body: Optional[LogoutRequest] = None, authorization: Optional[str] = Header(None)):
    if authorization:
        token = _get_token_from_header(authorization)
        delete_session(token)
    return AuthResponse(status="OK", message="Logout successful")


@router.post("/refresh", response_model=AuthResponse)
async def refresh(body: RefreshTokenRequest):
    session = refresh_session(body.refresh_token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = get_user_by_id(session["user_id"])
    return AuthResponse(
        status="OK",
        message="Token refreshed",
        user={"id": user["id"], "email": user["email"]} if user else None,
        session={
            "access_token": session["session_token"],
            "refresh_token": session["refresh_token"],
            "expires_at": session["expires_at"],
        },
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    update_session_activity(token)
    user = get_user_by_id(session["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    mfa = get_mfa_secret(user["id"])
    return UserInfo(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name"),
        email_verified=bool(user["email_verified"]),
        role=user["role"],
        plan=user.get("plan", "free"),
        mfa_enabled=bool(mfa and mfa.get("enabled")) if mfa else False,
        created_at=datetime.fromisoformat(user["created_at"]),
    )


@router.get("/me/sessions", response_model=List[SessionInfo])
async def get_my_sessions(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    sessions = get_user_sessions(session["user_id"])
    return [
        SessionInfo(
            id=s["id"],
            ip_address=s.get("ip_address"),
            user_agent=s.get("user_agent"),
            last_activity_at=datetime.fromisoformat(s["last_activity_at"]),
            created_at=datetime.fromisoformat(s["created_at"]),
            is_current=(s["session_token"] == token),
        )
        for s in sessions
    ]


@router.delete("/me/sessions/{session_id}", response_model=AuthResponse)
async def delete_session_by_id(session_id: str, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    with get_db() as conn:
        cur = conn.execute("DELETE FROM user_sessions WHERE id=? AND user_id=?", (session_id, session["user_id"]))
        conn.commit()
    if cur.rowcount > 0:
        return AuthResponse(status="OK", message="Session deleted")
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/me/devices", response_model=dict)
async def register_device(request: Request, body: DeviceCreateRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    existing = get_device_by_fingerprint(body.fingerprint)
    if existing and existing["user_id"] != session["user_id"]:
        raise HTTPException(status_code=409, detail="Device already registered to another user")
    device = create_device(
        session["user_id"],
        body.name,
        body.fingerprint,
        body.device_type,
        body.platform,
        body.browser,
    )
    return {"status": "OK", "device": device}


@router.get("/me/devices", response_model=List[DeviceInfo])
async def list_devices(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    devices = get_devices(session["user_id"])
    return [
        DeviceInfo(
            id=d["id"],
            name=d["name"],
            device_type=d["device_type"],
            platform=d.get("platform"),
            browser=d.get("browser"),
            trusted=bool(d["trusted"]),
            last_seen_at=datetime.fromisoformat(d["last_seen_at"]),
            created_at=datetime.fromisoformat(d["created_at"]),
        )
        for d in devices
    ]


@router.post("/me/devices/{device_id}/trust", response_model=AuthResponse)
async def trust_device_endpoint(device_id: str, body: DeviceTrustRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    trust_device(device_id, session["user_id"])
    return AuthResponse(status="OK", message="Device trusted")


@router.delete("/me/devices/{device_id}", response_model=AuthResponse)
async def delete_device_endpoint(device_id: str, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if delete_device(device_id, session["user_id"]):
        return AuthResponse(status="OK", message="Device deleted")
    raise HTTPException(status_code=404, detail="Device not found")


@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(body: PasswordResetRequest):
    user = get_user_by_email(body.email)
    if user:
        token = str(uuid.uuid4()) + str(uuid.uuid4())
        expires_at = (_now() + timedelta(hours=1)).isoformat()
        from app.services.auth_service import create_password_reset_token
        create_password_reset_token(user["id"], token, expires_at)
    return AuthResponse(status="OK", message="Password reset email sent if account exists")


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(body: PasswordResetConfirmRequest):
    from app.services.auth_service import reset_password_with_token
    user_id = reset_password_with_token(body.token, body.new_password)
    if user_id:
        delete_all_user_sessions(user_id)
        return AuthResponse(status="OK", message="Password reset successful")
    raise HTTPException(status_code=400, detail="Invalid or expired reset token")


@router.post("/change-password", response_model=AuthResponse)
async def change_password(body: ChangePasswordRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = get_user_by_id(session["user_id"])
    if not user or not verify_password(user, body.current_password):
        raise HTTPException(status_code=401, detail="Invalid current password")
    from app.services.auth_service import update_password
    update_password(user["id"], body.new_password)
    return AuthResponse(status="OK", message="Password changed successfully")


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(body: EmailVerificationRequest):
    from app.services.auth_service import verify_email_token
    result = verify_email_token(body.token)
    if result:
        return AuthResponse(status="OK", message="Email verified successfully")
    raise HTTPException(status_code=400, detail="Invalid or expired verification token")


@router.post("/magic-link", response_model=AuthResponse)
async def request_magic_link(body: MagicLinkRequest):
    user = get_user_by_email(body.email)
    if not user:
        return AuthResponse(status="OK", message="Magic link sent if account exists")
    magic_link = create_magic_link(user["id"], user["email"])
    return AuthResponse(
        status="OK",
        message="Magic link created",
        user={"id": user["id"], "email": user["email"], "magic_link_token": magic_link["token"]},
    )


@router.post("/magic-link/verify", response_model=AuthResponse)
async def verify_magic_link_endpoint(body: MagicLinkVerifyRequest):
    result = verify_magic_link(body.token)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired magic link")
    user = get_user_by_id(result["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session = create_session(user["id"])
    return AuthResponse(
        status="OK",
        message="Magic link login successful",
        user={"id": user["id"], "email": user["email"]},
        session={
            "access_token": session["session_token"],
            "refresh_token": session["refresh_token"],
            "expires_at": session["expires_at"],
        },
    )


@router.post("/mfa/setup", response_model=AuthResponse)
async def setup_mfa_endpoint(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    result = setup_mfa(session["user_id"])
    return AuthResponse(
        status="OK",
        message="MFA setup initiated",
        mfa_secret=result["secret"],
    )


@router.post("/mfa/verify", response_model=AuthResponse)
async def verify_mfa_endpoint(body: MFAVerifyRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if not verify_mfa(session["user_id"], body.code, body.backup_code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    enable_mfa(session["user_id"])
    if not body.backup_code:
        backup_codes = generate_backup_codes(session["user_id"])
        return AuthResponse(
            status="OK",
            message="MFA enabled successfully",
            mfa_backup_codes=backup_codes,
        )
    return AuthResponse(status="OK", message="MFA enabled successfully")


@router.post("/mfa/disable", response_model=AuthResponse)
async def disable_mfa_endpoint(body: MFADisableRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if not verify_mfa(session["user_id"], body.code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    disable_mfa(session["user_id"])
    return AuthResponse(status="OK", message="MFA disabled successfully")


@router.post("/oauth/{provider}", response_model=AuthResponse)
async def oauth_login(provider: str, body: OAuthLoginRequest):
    provider = provider.lower()
    supported = {"google", "github", "microsoft"}
    if provider not in supported:
        raise HTTPException(status_code=400, detail=f"Unsupported provider. Supported: {supported}")
    try:
        user = get_or_create_oauth_user(provider, body.access_token, body.email or "", body.full_name)
        session = create_session(user["id"])
        return AuthResponse(
            status="OK",
            message=f"OAuth login successful via {provider}",
            user={"id": user["id"], "email": user["email"]},
            session={
                "access_token": session["session_token"],
                "refresh_token": session["refresh_token"],
                "expires_at": session["expires_at"],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/oauth/{provider}/callback", response_model=AuthResponse)
async def oauth_callback(provider: str, body: OAuthCallbackRequest):
    provider = provider.lower()
    supported = {"google", "github", "microsoft"}
    if provider not in supported:
        raise HTTPException(status_code=400, detail=f"Unsupported provider. Supported: {supported}")
    try:
        token_data = await exchange_code(provider, body.code, "")
        access_token = token_data.get("access_token", "")
        user_info = await get_user_info(provider, access_token)
        email = user_info.get("email", "")
        provider_user_id = user_info.get("sub", user_info.get("id", ""))
        full_name = user_info.get("name")
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by OAuth provider")
        user = get_or_create_oauth_user(provider, provider_user_id, email, full_name)
        session = create_session(user["id"])
        return AuthResponse(
            status="OK",
            message=f"OAuth callback successful via {provider}",
            user={"id": user["id"], "email": user["email"]},
            session={
                "access_token": session["session_token"],
                "refresh_token": session["refresh_token"],
                "expires_at": session["expires_at"],
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/{provider}/url", response_model=dict)
async def get_oauth_url_endpoint(provider: str, redirect_uri: str, state: str):
    provider = provider.lower()
    url = get_oauth_url(provider, redirect_uri, state)
    return {"url": url}


@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key_endpoint(body: APIKeyCreateRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    key = create_api_key(session["user_id"], body.name, body.scopes)
    return APIKeyCreateResponse(
        id=key["id"],
        name=key["name"],
        key=key["key"],
        scopes=key["scopes"],
        created_at=datetime.fromisoformat(key["created_at"]),
    )


@router.get("/api-keys", response_model=List[APIKeyCreateResponse])
async def list_api_keys_endpoint(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    keys = list_api_keys(session["user_id"])
    return [
        APIKeyCreateResponse(
            id=k["id"],
            name=k["name"],
            key=None,
            scopes=k["scopes"],
            created_at=datetime.fromisoformat(k["created_at"]),
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}", response_model=AuthResponse)
async def revoke_api_key_endpoint(key_id: str, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if revoke_api_key(session["user_id"], key_id):
        return AuthResponse(status="OK", message="API key revoked")
    raise HTTPException(status_code=404, detail="API key not found")


@router.get("/roles", response_model=List[RoleInfo])
async def list_roles():
    from app.rbac import list_roles as _list_roles
    return [RoleInfo(**r) for r in _list_roles()]


@router.get("/permissions", response_model=List[dict])
async def list_permissions():
    from app.rbac import list_permissions as _list_permissions
    return _list_permissions()


@router.post("/roles", response_model=RoleInfo)
async def create_role_endpoint(body: RoleCreateRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    from app.rbac import create_role as _create_role
    role = _create_role(body.name, body.description)
    return RoleInfo(**role)


@router.post("/permissions", response_model=dict)
async def create_permission_endpoint(body: PermissionCreateRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    from app.rbac import create_permission as _create_permission
    perm = _create_permission(body.name, body.description)
    return perm


@router.post("/roles/permissions", response_model=AuthResponse)
async def assign_permission_to_role(body: RolePermissionAssignRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    from app.rbac import assign_permission_to_role as _assign
    _assign(body.role_id, body.permission_id)
    return AuthResponse(status="OK", message="Permission assigned to role")


@router.post("/users/roles", response_model=AuthResponse)
async def assign_role_to_user(body: UserRoleAssignRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = _get_token_from_header(authorization)
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    from app.rbac import assign_role_to_user as _assign
    _assign(body.user_id, body.role_id)
    return AuthResponse(status="OK", message="Role assigned to user")
