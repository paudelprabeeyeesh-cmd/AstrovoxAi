"""Enterprise SSO integrations router."""

from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.utils.auth.auth_utils import get_user_id_from_token
from .sso import enterprise_sso

router = APIRouter(prefix="/api/enterprise/sso", tags=["enterprise-sso"])


class RegisterOIDCRequest(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    scopes: Optional[List[str]] = ["openid", "profile", "email"]


class RegisterSAMLRequest(BaseModel):
    tenant_id: str
    entity_id: str
    sso_url: str
    slo_url: str
    x509_cert: str


class AuthURLRequest(BaseModel):
    tenant_id: str
    provider_type: str
    redirect_uri: str
    state: str


class TokenExchangeRequest(BaseModel):
    tenant_id: str
    code: str
    redirect_uri: str


@router.post("/oidc/register")
async def register_oidc(request: RegisterOIDCRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    config = {
        "client_id": request.client_id,
        "client_secret": request.client_secret,
        "issuer": request.issuer,
        "authorization_endpoint": request.authorization_endpoint,
        "token_endpoint": request.token_endpoint,
        "userinfo_endpoint": request.userinfo_endpoint,
        "scopes": request.scopes,
    }
    connection = enterprise_sso.register_oidc(request.tenant_id, config)
    return {"status": "OK", "connection_id": connection.connection_id}


@router.post("/saml/register")
async def register_saml(request: RegisterSAMLRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    config = {
        "entity_id": request.entity_id,
        "sso_url": request.sso_url,
        "slo_url": request.slo_url,
        "x509_cert": request.x509_cert,
    }
    connection = enterprise_sso.register_saml(request.tenant_id, config)
    return {"status": "OK", "connection_id": connection.connection_id}


@router.get("/{tenant_id}/connections")
async def list_sso_connections(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    connections = enterprise_sso.list_connections(tenant_id)
    return {
        "status": "OK",
        "connections": [
            {
                "connection_id": c.connection_id,
                "provider_type": c.provider_type,
                "is_active": c.is_active,
                "created_at": c.created_at,
            }
            for c in connections
        ],
    }


@router.post("/auth-url")
async def get_auth_url(request: AuthURLRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    url = enterprise_sso.build_authorization_url(request.tenant_id, request.provider_type, request.redirect_uri, request.state)
    return {"status": "OK", "auth_url": url}


@router.post("/oidc/token")
async def exchange_oidc_token(request: TokenExchangeRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    tokens = await enterprise_sso.exchange_code(request.tenant_id, request.code, request.redirect_uri)
    return {"status": "OK", "tokens": tokens}


@router.get("/oidc/userinfo")
async def get_oidc_userinfo(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    token = authorization.replace("Bearer ", "") if authorization else ""
    userinfo = await enterprise_sso.get_userinfo(tenant_id, token)
    return {"status": "OK", "userinfo": userinfo}


@router.post("/scim/provision")
async def scim_provision(tenant_id: str, scim_data: Dict[str, Any], authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    result = enterprise_sso.provision_scim_user(tenant_id, scim_data)
    return {"status": "OK", "provisioned": result}


@router.delete("/scim/users/{user_id}")
async def scim_deprovision(tenant_id: str, user_id: str, authorization: str = Header(None)):
    user_id_auth = get_user_id_from_token(authorization)
    success = enterprise_sso.deprovision_scim_user(tenant_id, user_id)
    return {"status": "OK", "deprovisioned": success}
