"""OAuth service for Google, GitHub, Microsoft providers."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from app.database import get_db


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


OAUTH_PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": ["openid", "profile", "email"],
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": ["user:email"],
    },
    "microsoft": {
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
        "scopes": ["openid", "profile", "email", "User.Read"],
    },
}


def get_oauth_url(provider: str, redirect_uri: str, state: str) -> str:
    config = OAUTH_PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"Unsupported OAuth provider: {provider}")
    params = {
        "client_id": _get_client_id(provider),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(config["scopes"]),
        "state": state,
    }
    return f"{config['authorize_url']}?{'&'.join(f'{k}={v}' for k, v in params.items())}"


def _get_client_id(provider: str) -> str:
    env_map = {
        "google": "GOOGLE_OAUTH_CLIENT_ID",
        "github": "GITHUB_OAUTH_CLIENT_ID",
        "microsoft": "MICROSOFT_OAUTH_CLIENT_ID",
    }
    import os
    return os.getenv(env_map.get(provider, ""), "")


def _get_client_secret(provider: str) -> str:
    env_map = {
        "google": "GOOGLE_OAUTH_CLIENT_SECRET",
        "github": "GITHUB_OAUTH_CLIENT_SECRET",
        "microsoft": "MICROSOFT_OAUTH_CLIENT_SECRET",
    }
    import os
    return os.getenv(env_map.get(provider, ""), "")


async def exchange_code(provider: str, code: str, redirect_uri: str) -> dict:
    config = OAUTH_PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"Unsupported OAuth provider: {provider}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config["token_url"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": _get_client_id(provider),
                "client_secret": _get_client_secret(provider),
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_user_info(provider: str, access_token: str) -> dict:
    config = OAUTH_PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"Unsupported OAuth provider: {provider}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            config["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


def get_or_create_oauth_user(provider: str, provider_user_id: str, email: str, full_name: Optional[str] = None) -> dict:
    existing = get_oauth_account_by_provider_user_id(provider, provider_user_id)
    if existing:
        user = get_user_by_id(existing["user_id"])
        if user:
            return user
    user = get_user_by_email(email)
    if not user:
        user_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(secrets.token_hex(32).encode()).hexdigest()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, role, plan, email_verified, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, email.lower(), password_hash, "user", "free", 1, _now().isoformat()),
            )
            conn.commit()
        user = {"id": user_id, "email": email.lower(), "role": "user", "plan": "free", "email_verified": 1}
    create_oauth_account(user["id"], provider, provider_user_id)
    return user


def create_oauth_account(user_id: str, provider: str, provider_user_id: str, access_token: Optional[str] = None, refresh_token: Optional[str] = None, expires_at: Optional[str] = None) -> dict:
    account_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO oauth_accounts (id, user_id, provider, provider_user_id, access_token, refresh_token, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (account_id, user_id, provider, provider_user_id, access_token, refresh_token, expires_at, _now().isoformat()),
        )
        conn.commit()
    return {"id": account_id, "provider": provider}


def get_oauth_account(user_id: str, provider: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM oauth_accounts WHERE user_id=? AND provider=?",
        (user_id, provider),
    ).fetchone()
    return dict(row) if row else None


def get_oauth_account_by_provider_user_id(provider: str, provider_user_id: str) -> Optional[dict]:
    row = get_db().__enter__().execute(
        "SELECT * FROM oauth_accounts WHERE provider=? AND provider_user_id=?",
        (provider, provider_user_id),
    ).fetchone()
    return dict(row) if row else None


def link_oauth_account(user_id: str, provider: str, provider_user_id: str, access_token: Optional[str] = None) -> dict:
    existing = get_oauth_account(user_id, provider)
    if existing:
        with get_db() as conn:
            conn.execute(
                "UPDATE oauth_accounts SET provider_user_id=?, access_token=? WHERE id=?",
                (provider_user_id, access_token, existing["id"]),
            )
            conn.commit()
        return existing
    return create_oauth_account(user_id, provider, provider_user_id, access_token)
