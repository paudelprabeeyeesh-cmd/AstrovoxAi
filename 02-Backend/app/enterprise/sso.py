"""Enterprise SSO integrations — OIDC, SAML, SCIM, Just-In-Time provisioning."""

import uuid
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
from dataclasses import dataclass, field

import httpx

from .tenancy import tenant_manager

logger = logging.getLogger(__name__)


@dataclass
class SSOConnection:
    connection_id: str
    tenant_id: str
    provider_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp)


class EnterpriseSSOManager:
    def __init__(self):
        self._connections: Dict[str, SSOConnection] = {}
        self._jwt_verifiers: Dict[str, Any] = {}

    def register_oidc(self, tenant_id: str, config: Dict[str, Any]) -> SSOConnection:
        connection_id = str(uuid.uuid4())
        connection = SSOConnection(
            connection_id=connection_id,
            tenant_id=tenant_id,
            provider_type="oidc",
            config=config,
        )
        self._connections[connection_id] = connection
        logger.info("Registered OIDC provider for tenant %s", tenant_id)
        return connection

    def register_saml(self, tenant_id: str, config: Dict[str, Any]) -> SSOConnection:
        connection_id = str(uuid.uuid4())
        connection = SSOConnection(
            connection_id=connection_id,
            tenant_id=tenant_id,
            provider_type="saml",
            config=config,
        )
        self._connections[connection_id] = connection
        logger.info("Registered SAML provider for tenant %s", tenant_id)
        return connection

    def get_connection(self, tenant_id: str, provider_type: str) -> Optional[SSOConnection]:
        for conn in self._connections.values():
            if conn.tenant_id == tenant_id and conn.provider_type == provider_type and conn.is_active:
                return conn
        return None

    def list_connections(self, tenant_id: str) -> List[SSOConnection]:
        return [c for c in self._connections.values() if c.tenant_id == tenant_id]

    def build_authorization_url(self, tenant_id: str, provider_type: str, redirect_uri: str, state: str) -> str:
        conn = self.get_connection(tenant_id, provider_type)
        if not conn:
            raise ValueError("SSO provider not configured")
        if provider_type == "oidc":
            cfg = conn.config
            params = {
                "client_id": cfg.get("client_id", ""),
                "response_type": "code",
                "scope": " ".join(cfg.get("scopes", ["openid", "profile", "email"])),
                "redirect_uri": redirect_uri,
                "state": state,
            }
            return f"{cfg.get('authorization_endpoint', '')}?{urlencode(params)}"
        if provider_type == "saml":
            cfg = conn.config
            return f"{cfg.get('sso_url', '')}?SAMLRequest={state}"
        raise ValueError(f"Unsupported provider type: {provider_type}")

    async def exchange_code(self, tenant_id: str, code: str, redirect_uri: str) -> Dict[str, Any]:
        conn = self.get_connection(tenant_id, "oidc")
        if not conn:
            raise ValueError("OIDC provider not configured")
        cfg = conn.config
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                cfg.get("token_endpoint", ""),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": cfg.get("client_id", ""),
                    "client_secret": cfg.get("client_secret", ""),
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_userinfo(self, tenant_id: str, access_token: str) -> Dict[str, Any]:
        conn = self.get_connection(tenant_id, "oidc")
        if not conn:
            raise ValueError("OIDC provider not configured")
        cfg = conn.config
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                cfg.get("userinfo_endpoint", ""),
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    def provision_scim_user(self, tenant_id: str, scim_data: Dict[str, Any]) -> dict:
        email = scim_data.get("emails", [{}])[0].get("value", "")
        if not email:
            raise ValueError("Email required for SCIM provisioning")
        return {"user_id": str(uuid.uuid4()), "email": email, "provisioned": True}

    def deprovision_scim_user(self, tenant_id: str, user_id: str) -> bool:
        return True

    def deactivate_connection(self, connection_id: str) -> bool:
        conn = self._connections.get(connection_id)
        if not conn:
            return False
        conn.is_active = False
        return True


enterprise_sso = EnterpriseSSOManager()
