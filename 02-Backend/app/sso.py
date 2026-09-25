import uuid
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

import httpx
from repositories.database.client import get_db
from services.auth.auth import hash_password
from .audit import log_action

logger = logging.getLogger(__name__)


class SSOProviderType:
    OIDC = "oidc"
    SAML = "saml"


class OIDCProvider:
    def __init__(self, config: Dict[str, Any]):
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.issuer = config.get("issuer", "")
        self.authorization_endpoint = config.get("authorization_endpoint", "")
        self.token_endpoint = config.get("token_endpoint", "")
        self.userinfo_endpoint = config.get("userinfo_endpoint", "")
        self.scopes = config.get("scopes", ["openid", "profile", "email"])

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{self.authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()


class SAMLProvider:
    def __init__(self, config: Dict[str, Any]):
        self.entity_id = config.get("entity_id", "")
        self.sso_url = config.get("sso_url", "")
        self.x509_cert = config.get("x509_cert", "")
        self.issuer = config.get("issuer", "")

    def build_auth_request(self, relay_state: str) -> str:
        return f"SAMLRequest={relay_state}"

    async def parse_assertion(self, assertion: str) -> Dict[str, Any]:
        return {"assertion": assertion, "parsed_at": datetime.now(timezone.utc).isoformat()}


class SSOService:
    def __init__(self):
        self._providers: Dict[str, Dict[str, Any]] = {}

    def register_provider(self, org_id: str, provider_type: str, config: Dict[str, Any]) -> dict:
        provider_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO sso_connections (id, org_id, provider_type, config, created_at) VALUES (?, ?, ?, ?, ?)",
                (provider_id, org_id, provider_type, json.dumps(config), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": provider_id, "org_id": org_id, "provider_type": provider_type}

    def get_provider(self, org_id: str, provider_type: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM sso_connections WHERE org_id = ? AND provider_type = ?",
                (org_id, provider_type),
            ).fetchone()
            if row:
                data = dict(row)
                data["config"] = json.loads(data["config"] or "{}")
                return data
            return None

    async def authenticate_with_oidc(self, org_id: str, token: str) -> dict:
        provider_data = self.get_provider(org_id, SSOProviderType.OIDC)
        if not provider_data:
            raise ValueError("OIDC provider not configured for this organization")
        provider = OIDCProvider(provider_data["config"])
        userinfo = await provider.get_userinfo(token)
        return self._find_or_create_sso_user(org_id, SSOProviderType.OIDC, userinfo)

    async def authenticate_with_saml(self, org_id: str, assertion: str) -> dict:
        provider_data = self.get_provider(org_id, SSOProviderType.SAML)
        if not provider_data:
            raise ValueError("SAML provider not configured for this organization")
        provider = SAMLProvider(provider_data["config"])
        parsed = await provider.parse_assertion(assertion)
        return self._find_or_create_sso_user(org_id, SSOProviderType.SAML, parsed)

    def _find_or_create_sso_user(self, org_id: str, provider_type: str, profile: Dict[str, Any]) -> dict:
        email = profile.get("email") or profile.get("mail", "")
        if not email:
            raise ValueError("Email not found in SSO profile")
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM sso_users WHERE org_id = ? AND provider = ? AND email = ?",
                (org_id, provider_type, email),
            ).fetchone()
            if row:
                user_id = row["user_id"]
            else:
                user_id = str(uuid.uuid4())
                password_hash = hash_password(uuid.uuid4().hex)
                try:
                    conn.execute(
                        "INSERT INTO users (id, email, password_hash, email_verified, role, plan) VALUES (?, ?, ?, ?, ?, ?)",
                        (user_id, email, password_hash, 1, "user", "enterprise"),
                    )
                except Exception:
                    row2 = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                    if row2:
                        user_id = row2["id"]
                conn.execute(
                    "INSERT INTO sso_users (id, org_id, provider, provider_user_id, email, user_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        org_id,
                        provider_type,
                        profile.get("sub", profile.get("name_id", "")),
                        email,
                        user_id,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            conn.commit()
        return {"user_id": user_id, "email": email, "provider": provider_type}

    def provision_scim_user(self, org_id: str, scim_data: Dict[str, Any]) -> dict:
        email = scim_data.get("emails", [{}])[0].get("value", "")
        if not email:
            raise ValueError("Email required for SCIM provisioning")
        with get_db() as conn:
            row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if row:
                user_id = row["id"]
            else:
                user_id = str(uuid.uuid4())
                password_hash = hash_password(uuid.uuid4().hex)
                conn.execute(
                    "INSERT INTO users (id, email, password_hash, email_verified, role, plan) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, email, password_hash, 1, scim_data.get("role", "user"), "enterprise"),
                )
            conn.commit()
        return {"user_id": user_id, "email": email}

    def deprovision_scim_user(self, org_id: str, user_id: str) -> bool:
        with get_db() as conn:
            cur = conn.execute(
                "DELETE FROM sso_users WHERE org_id = ? AND user_id = ?",
                (org_id, user_id),
            )
            conn.commit()
            return cur.rowcount > 0


sso_service = SSOService()
