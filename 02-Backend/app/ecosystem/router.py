"""Ecosystem FastAPI router.

Exposes:
- Plugin lifecycle endpoints
- Public developer API (key issuance, OAuth, analytics)
- Webhook subscription + delivery endpoints
- Third-party integration connections
- Marketplace catalog, search, ratings, install/uninstall
- Ecosystem monitoring summary
- Audit log retrieval

Mounted at /ecosystem/* by ``main.py``.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..auth_utils import get_current_user
from ..logging_config import get_logger

from .api_platform import (
    DEFAULT_POLICIES,
    ApiErrorCode,
    ApiKey,
    RateLimitPolicy,
    build_error_response,
    get_api_analytics,
    get_api_registry,
    get_key_store,
    get_oauth_server,
    get_rate_limiter,
)
from .integrations import (
    IntegrationClient,
    IntegrationConnection,
    IntegrationProvider,
    get_integration_client,
    get_integration_registry,
    get_integration_store,
)
from .marketplace import (
    Listing,
    ListingRating,
    get_marketplace_catalog,
    seed_default_catalog,
)
from .monitoring import get_ecosystem_monitor
from .plugins import (
    PluginLifecycleError,
    PluginManifest,
    PluginPermission,
    PluginPermissionError,
    PluginState,
    get_plugin_manager,
)
from .security import (
    AuditLog,
    DependencyScanner,
    SecretScrubber,
    SecretVault,
    get_audit_log,
)
from .webhooks import (
    WebhookEvent,
    WebhookManager,
    get_webhook_manager,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/ecosystem", tags=["ecosystem"])


# ---------------------------------------------------------------------------
# Plugin framework
# ---------------------------------------------------------------------------


class PluginInstallRequest(BaseModel):
    source: str = Field(..., description="Plugin id, directory, or archive path")
    permissions: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    requested_id: Optional[str] = None


class PluginConfigUpdate(BaseModel):
    config: Dict[str, Any]


class PluginPermissionsUpdate(BaseModel):
    permissions: List[str]


class PluginInvokeRequest(BaseModel):
    method: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)


@router.get("/plugins")
async def list_plugins(
    state: Optional[PluginState] = None,
    user=Depends(get_current_user),
):
    manager = get_plugin_manager()
    records = manager.registry.all()
    if state:
        records = [r for r in records if r.state == state]
    return {
        "count": len(records),
        "plugins": [r.to_dict() for r in records],
    }


@router.get("/plugins/discover")
async def discover_plugins(user=Depends(get_current_user)):
    manager = get_plugin_manager()
    manifests = manager.discover()
    return {
        "count": len(manifests),
        "manifests": [m.to_dict() for m in manifests],
    }


@router.post("/plugins/install")
async def install_plugin(
    req: PluginInstallRequest,
    user=Depends(get_current_user),
):
    manager = get_plugin_manager()
    try:
        record = manager.install(
            source=req.source,
            permissions=req.permissions,
            config=req.config,
            requested_id=req.requested_id,
        )
    except PluginLifecycleError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_error_response(
                ApiErrorCode.BAD_REQUEST, str(exc), 400
            ).detail,
        )
    get_ecosystem_monitor().record(
        "plugin.installed",
        {"plugin_id": record.manifest.id, "version": record.manifest.version},
        plugin_id=record.manifest.id,
    )
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="plugin.install",
        target=record.manifest.id,
        metadata={"version": record.manifest.version},
    )
    return record.to_dict()


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str, user=Depends(get_current_user)):
    manager = get_plugin_manager()
    try:
        record = manager.enable(plugin_id)
    except PluginLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    get_ecosystem_monitor().record("plugin.enabled", {}, plugin_id=plugin_id)
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="plugin.enable",
        target=plugin_id,
    )
    return record.to_dict()


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str, user=Depends(get_current_user)):
    manager = get_plugin_manager()
    record = manager.disable(plugin_id)
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="plugin.disable",
        target=plugin_id,
    )
    return record.to_dict()


@router.delete("/plugins/{plugin_id}")
async def uninstall_plugin(plugin_id: str, user=Depends(get_current_user)):
    manager = get_plugin_manager()
    try:
        record = manager.uninstall(plugin_id)
    except PluginLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    get_ecosystem_monitor().record("plugin.uninstalled", {}, plugin_id=plugin_id)
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="plugin.uninstall",
        target=plugin_id,
    )
    return {"status": "ok", "record": record.to_dict()}


@router.post("/plugins/{plugin_id}/update")
async def update_plugin(
    plugin_id: str,
    new_version: str,
    new_source: Optional[str] = None,
    user=Depends(get_current_user),
):
    manager = get_plugin_manager()
    record = manager.update(plugin_id, new_version, new_source)
    get_ecosystem_monitor().record(
        "plugin.updated",
        {"new_version": new_version},
        plugin_id=plugin_id,
    )
    return record.to_dict()


@router.put("/plugins/{plugin_id}/config")
async def update_plugin_config(
    plugin_id: str,
    payload: PluginConfigUpdate,
    user=Depends(get_current_user),
):
    manager = get_plugin_manager()
    record = manager.set_config(plugin_id, payload.config)
    return record.to_dict()


@router.post("/plugins/{plugin_id}/permissions")
async def grant_plugin_permissions(
    plugin_id: str,
    payload: PluginPermissionsUpdate,
    user=Depends(get_current_user),
):
    manager = get_plugin_manager()
    record = manager.grant(plugin_id, payload.permissions)
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="plugin.permissions.grant",
        target=plugin_id,
        metadata={"permissions": payload.permissions},
    )
    return record.to_dict()


@router.delete("/plugins/{plugin_id}/permissions")
async def revoke_plugin_permissions(
    plugin_id: str,
    permissions: List[str] = Query(...),
    user=Depends(get_current_user),
):
    manager = get_plugin_manager()
    record = manager.revoke(plugin_id, permissions)
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="plugin.permissions.revoke",
        target=plugin_id,
        metadata={"permissions": permissions},
    )
    return record.to_dict()


@router.post("/plugins/{plugin_id}/invoke")
async def invoke_plugin(
    plugin_id: str,
    payload: PluginInvokeRequest,
    user=Depends(get_current_user),
):
    manager = get_plugin_manager()
    try:
        result = manager.invoke(plugin_id, payload.method, *payload.args, **payload.kwargs)
    except (PluginLifecycleError, PluginPermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    get_ecosystem_monitor().record(
        "plugin.invocation",
        {"method": payload.method},
        plugin_id=plugin_id,
    )
    return {"ok": True, "result": result}


@router.get("/plugins/permissions")
async def list_permissions():
    return {
        "permissions": [
            {"name": p.value, "description": _PERMISSION_HELP.get(p, "")}
            for p in PluginPermission
        ]
    }


_PERMISSION_HELP = {
    PluginPermission.READ_MEMORY: "Read long-term memory entries.",
    PluginPermission.WRITE_MEMORY: "Create or modify memory entries.",
    PluginPermission.READ_FILES: "Read files from AstrovoxAI storage.",
    PluginPermission.WRITE_FILES: "Write or delete files.",
    PluginPermission.NETWORK_OUT: "Make outbound HTTP calls.",
    PluginPermission.NETWORK_IN: "Receive inbound HTTP calls.",
    PluginPermission.EXECUTE_CODE: "Execute code in a sandbox.",
    PluginPermission.ACCESS_USERS: "Read other users' profile data.",
    PluginPermission.ACCESS_BILLING: "Read billing information.",
    PluginPermission.AGENT_RUN: "Start agent runs.",
    PluginPermission.WEBHOOK_PUBLISH: "Publish webhook events.",
    PluginPermission.STORAGE_READ: "Read objects from storage.",
    PluginPermission.STORAGE_WRITE: "Write objects to storage.",
}


# ---------------------------------------------------------------------------
# API Platform
# ---------------------------------------------------------------------------


class ApiKeyIssueRequest(BaseModel):
    label: str
    scopes: List[str]
    tier: str = "authenticated"
    description: str = ""


class OAuthClientRegisterRequest(BaseModel):
    name: str
    redirect_uris: List[str]
    scopes: Optional[List[str]] = None


class OAuthAuthorizeRequest(BaseModel):
    client_id: str
    redirect_uri: str
    scope: str = "read"
    state: Optional[str] = None


class OAuthTokenRequest(BaseModel):
    grant_type: str = Field(..., pattern="^(authorization_code|client_credentials|refresh_token)$")
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


@router.get("/api/endpoints")
async def list_api_endpoints():
    registry = get_api_registry()
    return {"version": "v1", "endpoints": registry.list("v1")}


@router.post("/api/keys")
async def issue_api_key(req: ApiKeyIssueRequest, user=Depends(get_current_user)):
    store = get_key_store()
    record, key, secret = store.issue(
        owner_id=user.get("id", "anonymous"),
        label=req.label,
        scopes=req.scopes,
        tier=req.tier,
        description=req.description,
    )
    get_ecosystem_monitor().record(
        "api.key.created",
        {"key_id": record.id, "tier": record.tier},
    )
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="api.key.create",
        target=record.id,
    )
    return {
        "id": record.id,
        "label": record.label,
        "scopes": record.scopes,
        "tier": record.tier,
        "key": key,
        "secret": secret,
        "warning": "Store the secret securely; it will not be shown again.",
    }


@router.get("/api/keys")
async def list_api_keys(user=Depends(get_current_user)):
    store = get_key_store()
    records = store.list(user.get("id"))
    return {"keys": [r.to_dict() for r in records]}


@router.delete("/api/keys/{key_id}")
async def revoke_api_key(key_id: str, user=Depends(get_current_user)):
    store = get_key_store()
    record = store.revoke(key_id)
    if record is None:
        raise HTTPException(status_code=404, detail="API key not found")
    get_ecosystem_monitor().record(
        "api.key.revoked",
        {"key_id": key_id},
    )
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="api.key.revoke",
        target=key_id,
    )
    return record.to_dict()


@router.get("/api/analytics")
async def api_analytics(user=Depends(get_current_user)):
    analytics = get_api_analytics()
    return analytics.summary()


@router.get("/api/analytics/perf")
async def api_analytics_perf(endpoint: str, user=Depends(get_current_user)):
    return get_api_analytics().endpoint_perf(endpoint)


@router.get("/api/rate-limits")
async def api_rate_limits(user=Depends(get_current_user)):
    return {"policies": get_rate_limiter().status()}


@router.post("/api/rate-limits")
async def add_rate_limit(policy: RateLimitPolicy, user=Depends(get_current_user)):
    if user.get("role") not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    get_rate_limiter().add_policy(policy)
    return policy.to_dict()


# OAuth endpoints
@router.post("/api/oauth/clients")
async def register_oauth_client(req: OAuthClientRegisterRequest, user=Depends(get_current_user)):
    server = get_oauth_server()
    client, secret = server.register_client(
        name=req.name, redirect_uris=req.redirect_uris, scopes=req.scopes
    )
    return {
        "client_id": client.id,
        "client_secret": secret,
        "redirect_uris": client.redirect_uris,
        "scopes": client.scopes,
    }


@router.post("/api/oauth/authorize")
async def oauth_authorize(req: OAuthAuthorizeRequest, user=Depends(get_current_user)):
    server = get_oauth_server()
    client = server.clients.get(req.client_id)
    if client is None or req.redirect_uri not in client.redirect_uris:
        raise HTTPException(status_code=400, detail="Invalid client or redirect_uri")
    code = server.authorization_code(
        client_id=req.client_id,
        user_id=user.get("id", "anonymous"),
        redirect_uri=req.redirect_uri,
        scope=req.scope,
        state=req.state,
    )
    return {"code": code, "state": req.state}


@router.post("/api/oauth/token")
async def oauth_token(req: OAuthTokenRequest):
    server = get_oauth_server()
    if req.grant_type == "authorization_code":
        token = server.exchange_code(
            code=req.code or "",
            client_id=req.client_id or "",
            redirect_uri=req.redirect_uri or "",
        )
    elif req.grant_type == "client_credentials":
        client = server.authenticate_client(req.client_id or "", req.client_secret or "")
        if client is None:
            raise HTTPException(status_code=401, detail="Invalid client credentials")
        token = server.client_credentials(req.client_id, req.scope or "")
    elif req.grant_type == "refresh_token":
        token = server.refresh(req.refresh_token or "")
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant type")
    if token is None:
        raise HTTPException(status_code=400, detail="Token exchange failed")
    return {
        "access_token": token.access_token,
        "token_type": token.token_type,
        "expires_in": token.expires_in,
        "refresh_token": token.refresh_token,
        "scope": token.scope,
    }


@router.get("/api/oauth/introspect")
async def oauth_introspect(token: str):
    server = get_oauth_server()
    return server.introspect(token) or {"active": False}


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


class WebhookCreateRequest(BaseModel):
    url: str
    events: List[str]
    description: str = ""
    filters: Optional[Dict[str, Any]] = None


class WebhookPublishRequest(BaseModel):
    event: str
    payload: Dict[str, Any]


@router.get("/webhooks/events")
async def list_webhook_events():
    return {
        "events": [
            {"name": e.value, "description": _EVENT_DESCRIPTIONS.get(e, "")}
            for e in WebhookEvent
        ]
    }


_EVENT_DESCRIPTIONS = {
    WebhookEvent.CHAT_COMPLETED: "A chat completion finished successfully.",
    WebhookEvent.CHAT_FAILED: "A chat completion failed.",
    WebhookEvent.AGENT_COMPLETED: "An agent run finished.",
    WebhookEvent.AGENT_FAILED: "An agent run failed.",
    WebhookEvent.KNOWLEDGE_INGESTED: "A knowledge document was ingested.",
    WebhookEvent.PLUGIN_INSTALLED: "A plugin was installed.",
    WebhookEvent.PLUGIN_UNINSTALLED: "A plugin was uninstalled.",
    WebhookEvent.PLUGIN_UPDATED: "A plugin was updated.",
    WebhookEvent.INTEGRATION_CONNECTED: "An integration was connected.",
    WebhookEvent.INTEGRATION_DISCONNECTED: "An integration was disconnected.",
    WebhookEvent.API_KEY_CREATED: "A new API key was issued.",
    WebhookEvent.API_KEY_REVOKED: "An API key was revoked.",
    WebhookEvent.USER_CREATED: "A new user account was created.",
    WebhookEvent.WORKSPACE_CREATED: "A workspace was created.",
    WebhookEvent.CUSTOM: "Custom event published by API callers.",
}


@router.post("/webhooks/subscriptions")
async def create_webhook(req: WebhookCreateRequest, user=Depends(get_current_user)):
    manager = get_webhook_manager()
    sub = manager.create_subscription(
        url=req.url,
        events=req.events,
        owner_id=user.get("id", "anonymous"),
        description=req.description,
        filters=req.filters,
    )
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="webhook.subscribe",
        target=sub.id,
        metadata={"url": sub.url, "events": sub.events},
    )
    return {
        "id": sub.id,
        "url": sub.url,
        "events": sub.events,
        "secret": sub.secret,
        "active": sub.active,
        "warning": "Save the secret; it's used to verify webhook signatures.",
    }


@router.get("/webhooks/subscriptions")
async def list_webhooks(user=Depends(get_current_user)):
    manager = get_webhook_manager()
    subs = manager.list_subscriptions(user.get("id"))
    return {
        "count": len(subs),
        "subscriptions": [
            {
                "id": s.id,
                "url": s.url,
                "events": s.events,
                "description": s.description,
                "active": s.active,
                "created_at": s.created_at,
                "filters": s.filters,
                "last_delivery": s.last_delivery,
                "failure_count": s.failure_count,
            }
            for s in subs
        ],
    }


@router.delete("/webhooks/subscriptions/{sub_id}")
async def delete_webhook(sub_id: str, user=Depends(get_current_user)):
    manager = get_webhook_manager()
    sub = manager.delete_subscription(sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="webhook.unsubscribe",
        target=sub_id,
    )
    return {"status": "deleted"}


@router.post("/webhooks/subscriptions/{sub_id}/pause")
async def pause_webhook(sub_id: str, user=Depends(get_current_user)):
    manager = get_webhook_manager()
    sub = manager.pause(sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"id": sub.id, "active": sub.active}


@router.post("/webhooks/subscriptions/{sub_id}/resume")
async def resume_webhook(sub_id: str, user=Depends(get_current_user)):
    manager = get_webhook_manager()
    sub = manager.resume(sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"id": sub.id, "active": sub.active}


@router.post("/webhooks/publish")
async def publish_webhook(
    req: WebhookPublishRequest,
    user=Depends(get_current_user),
):
    manager = get_webhook_manager()
    deliveries = await manager.publish(
        req.event, req.payload, target_owner=user.get("id")
    )
    get_ecosystem_monitor().record(
        "webhook.published",
        {"event": req.event, "count": len(deliveries)},
    )
    return {
        "event": req.event,
        "deliveries": [
            {"id": d.id, "subscription_id": d.subscription_id, "status": d.status}
            for d in deliveries
        ],
    }


@router.get("/webhooks/deliveries")
async def list_deliveries(limit: int = 100):
    manager = get_webhook_manager()
    log = await manager.delivery_store.tail(limit)
    return {"count": len(log), "deliveries": log}


@router.get("/webhooks/dlq")
async def list_dlq(limit: int = 100):
    manager = get_webhook_manager()
    items = await manager.dlq.drain(limit)
    return {"count": len(items), "items": items}


@router.get("/webhooks/analytics")
async def webhook_analytics():
    manager = get_webhook_manager()
    return manager.metrics()


@router.post("/webhooks/verify")
async def verify_webhook_signature(
    request: Request,
    x_astrovox_signature: str = Header(..., alias="X-Astrovox-Signature"),
    x_astrovox_timestamp: Optional[str] = Header(default=None, alias="X-Astrovox-Timestamp"),
    secret: str = Query(...),
):
    body = await request.body()
    manager = get_webhook_manager()
    valid = manager.verify_incoming(
        body, x_astrovox_signature, secret, x_astrovox_timestamp
    )
    return {"valid": valid}


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------


class IntegrationConnectRequest(BaseModel):
    provider: str
    label: str
    scopes: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IntegrationActionRequest(BaseModel):
    action: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)


@router.get("/integrations/catalog")
async def list_integration_catalog():
    registry = get_integration_registry()
    return {"count": len(registry.list()), "integrations": registry.list()}


@router.get("/integrations/categories")
async def list_integration_categories():
    registry = get_integration_registry()
    categories = sorted({i["category"] for i in registry.list()})
    return {
        "categories": [
            {"name": cat, "items": registry.by_category(cat)} for cat in categories
        ]
    }


@router.post("/integrations/connections")
async def connect_integration(
    req: IntegrationConnectRequest,
    user=Depends(get_current_user),
):
    try:
        provider = IntegrationProvider(req.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    store = get_integration_store()
    connection = IntegrationConnection(
        id=f"int_{int(time.time() * 1000)}",
        provider=provider,
        owner_id=user.get("id", "anonymous"),
        label=req.label,
        status="connected",
        scopes=req.scopes or [],
        config=req.config or {},
        access_token=req.access_token,
        refresh_token=req.refresh_token,
        metadata=req.metadata or {},
    )
    store.add(connection)
    get_ecosystem_monitor().record(
        "integration.connected",
        {"provider": provider.value},
        integration=provider.value,
    )
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="integration.connect",
        target=connection.id,
        metadata={"provider": provider.value, "label": req.label},
    )
    return connection.to_dict()


@router.get("/integrations/connections")
async def list_integration_connections(user=Depends(get_current_user)):
    store = get_integration_store()
    conns = store.by_owner(user.get("id"))
    return {"count": len(conns), "connections": [c.to_dict() for c in conns]}


@router.delete("/integrations/connections/{connection_id}")
async def disconnect_integration(
    connection_id: str, user=Depends(get_current_user)
):
    store = get_integration_store()
    conn = store.get(connection_id)
    if conn is None or conn.owner_id != user.get("id"):
        raise HTTPException(status_code=404, detail="Connection not found")
    store.remove(connection_id)
    get_ecosystem_monitor().record(
        "integration.disconnected",
        {"provider": conn.provider.value},
        integration=conn.provider.value,
    )
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="integration.disconnect",
        target=connection_id,
        metadata={"provider": conn.provider.value},
    )
    return {"status": "disconnected"}


@router.post("/integrations/connections/{connection_id}/invoke")
async def invoke_integration(
    connection_id: str,
    payload: IntegrationActionRequest,
    user=Depends(get_current_user),
):
    client = get_integration_client()
    method_name = f"{payload.action}"
    fn = getattr(client, method_name, None)
    if fn is None:
        raise HTTPException(status_code=400, detail=f"Unknown action '{payload.action}'")
    try:
        result = fn(connection_id, *payload.args, **payload.kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    get_ecosystem_monitor().record(
        "integration.invocation",
        {"action": payload.action},
    )
    return result


# ---------------------------------------------------------------------------
# Marketplace
# ---------------------------------------------------------------------------


class MarketplaceRatingRequest(BaseModel):
    stars: int
    review: str = ""


@router.get("/marketplace/listings")
async def list_marketplace_listings(
    q: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort: str = "popular",
    limit: int = 50,
):
    catalog = get_marketplace_catalog()
    seed_default_catalog()
    catalog.sync_installed()
    return {
        "count": len(catalog.listings),
        "results": catalog.search(
            query=q,
            category=category,
            tag=tag,
            sort=sort,
            limit=limit,
        ),
    }


@router.get("/marketplace/categories")
async def marketplace_categories():
    catalog = get_marketplace_catalog()
    return {"categories": catalog.categories()}


@router.get("/marketplace/listings/{listing_id}")
async def get_marketplace_listing(listing_id: str):
    catalog = get_marketplace_catalog()
    listing = catalog.listings.get(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {
        "listing": listing.to_dict(),
        "ratings": catalog.ratings_for(listing_id),
    }


@router.post("/marketplace/listings/{listing_id}/install")
async def marketplace_install(
    listing_id: str,
    permissions: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None,
    user=Depends(get_current_user),
):
    catalog = get_marketplace_catalog()
    try:
        result = catalog.install(listing_id, permissions, config)
    except PluginLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="marketplace.install",
        target=listing_id,
    )
    return result


@router.delete("/marketplace/listings/{listing_id}")
async def marketplace_uninstall(
    listing_id: str,
    user=Depends(get_current_user),
):
    catalog = get_marketplace_catalog()
    try:
        result = catalog.uninstall(listing_id)
    except PluginLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    get_audit_log().record(
        actor=user.get("email", user.get("id", "system")),
        action="marketplace.uninstall",
        target=listing_id,
    )
    return result


@router.post("/marketplace/listings/{listing_id}/toggle")
async def marketplace_toggle(
    listing_id: str,
    enabled: bool,
    user=Depends(get_current_user),
):
    catalog = get_marketplace_catalog()
    try:
        result = catalog.toggle(listing_id, enabled)
    except PluginLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@router.post("/marketplace/listings/{listing_id}/ratings")
async def marketplace_rate(
    listing_id: str,
    req: MarketplaceRatingRequest,
    user=Depends(get_current_user),
):
    catalog = get_marketplace_catalog()
    rating = ListingRating(
        user_id=user.get("id", "anonymous"),
        stars=req.stars,
        review=req.review,
    )
    listing = catalog.add_rating(listing_id, rating)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing.to_dict()


@router.get("/marketplace/notifications")
async def marketplace_notifications(user=Depends(get_current_user)):
    catalog = get_marketplace_catalog()
    return {"notifications": catalog.notifications()}


# ---------------------------------------------------------------------------
# Monitoring + audit + security
# ---------------------------------------------------------------------------


@router.get("/monitoring/summary")
async def monitoring_summary(user=Depends(get_current_user)):
    return get_ecosystem_monitor().summary()


@router.get("/monitoring/health")
async def monitoring_health():
    return get_ecosystem_monitor().health()


@router.get("/monitoring/adoption")
async def monitoring_adoption(user=Depends(get_current_user)):
    return get_ecosystem_monitor().adoption()


@router.get("/monitoring/events")
async def monitoring_recent(limit: int = 50, user=Depends(get_current_user)):
    return {"events": get_ecosystem_monitor().recent(limit)}


@router.get("/audit")
async def audit_log(
    actor: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    user=Depends(get_current_user),
):
    return {
        "entries": get_audit_log().tail(limit),
        "filter": {"actor": actor, "action": action},
    }


class DependencyScanRequest(BaseModel):
    requirements: Optional[str] = None
    source: Optional[str] = None


@router.post("/security/scan")
async def dependency_scan(req: DependencyScanRequest, user=Depends(get_current_user)):
    scanner = DependencyScanner()
    findings = []
    if req.requirements:
        findings.extend(scanner.scan_requirements(req.requirements))
    if req.source:
        findings.extend(scanner.scan_source(req.source))
    return {"count": len(findings), "findings": [f.to_dict() for f in findings]}


class SecretVaultRequest(BaseModel):
    value: str


@router.post("/security/secrets/encrypt")
async def secret_encrypt(req: SecretVaultRequest):
    vault = SecretVault()
    return {"ciphertext": vault.encrypt(req.value)}


@router.post("/security/secrets/decrypt")
async def secret_decrypt(payload: SecretVaultRequest):
    vault = SecretVault()
    try:
        plaintext = vault.decrypt(payload.value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"plaintext": plaintext}


# ---------------------------------------------------------------------------
# Public entry point (no auth required) for SDKs / health checks
# ---------------------------------------------------------------------------


@router.get("/public/info")
async def public_info():
    return {
        "name": "AstrovoxAI Developer Platform",
        "version": "1.0.0",
        "api_version": "v1",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": {
            "plugins": "/ecosystem/plugins",
            "api_keys": "/ecosystem/api/keys",
            "oauth": "/ecosystem/api/oauth/token",
            "webhooks": "/ecosystem/webhooks/subscriptions",
            "integrations": "/ecosystem/integrations/catalog",
            "marketplace": "/ecosystem/marketplace/listings",
            "audit": "/ecosystem/audit",
        },
    }


@router.get("/public/health")
async def public_health():
    return {
        "status": "ok",
        "service": "astrovox-ecosystem",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }