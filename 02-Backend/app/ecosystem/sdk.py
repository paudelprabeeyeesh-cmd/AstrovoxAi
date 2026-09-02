"""Official Python SDK for the AstrovoxAI Developer Platform.

This module is the canonical reference SDK used by examples and unit tests.
It can be imported by external services (``pip install astrovoxai`` or vendored)
and is intentionally self-contained so it works without installing FastAPI.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


class AstrovoxError(Exception):
    """Base error type raised by the SDK."""

    def __init__(self, message: str, status: Optional[int] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


@dataclass
class AstrovoxClient:
    """High-level SDK client.

    The client bundles authentication (API key + secret), helpers for
    common endpoints, and webhook signature utilities.  ``transport`` can
    be overridden for testing.
    """

    base_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    timeout: float = 30.0
    transport: Any = None
    user_agent: str = "astrovox-python-sdk/1.0"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = urllib.parse.urljoin(self.base_url + "/", path.lstrip("/"))
        if params:
            url = f"{url}?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req_headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if data is not None:
            req_headers["Content-Type"] = "application/json"
        if self.access_token:
            req_headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.api_key:
            req_headers["X-API-Key"] = self.api_key
            if self.api_secret:
                req_headers["X-API-Secret"] = self.api_secret
        if headers:
            req_headers.update(headers)
        request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        if self.transport is not None:
            response = self.transport(request)
        else:
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                    raw = resp.read()
                    return json.loads(raw.decode("utf-8")) if raw else {}
            except urllib.error.HTTPError as exc:
                raw = exc.read()
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception:
                    payload = {"error": raw.decode("utf-8", errors="ignore")}
                raise AstrovoxError(
                    payload.get("error", {}).get("message", exc.reason),
                    status=exc.code,
                    payload=payload,
                ) from exc
            except urllib.error.URLError as exc:
                raise AstrovoxError(f"Network error: {exc.reason}") from exc
        return response

    # ---------------- Chat / completions ----------------

    def chat(self, messages: List[Dict[str, str]], *, model: str = "auto", **options: Any) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/v1/chat/completions",
            body={"model": model, "messages": messages, **options},
        )

    # ---------------- Plugins ----------------

    def list_plugins(self) -> Dict[str, Any]:
        return self._request("GET", "/ecosystem/plugins")

    def install_plugin(
        self,
        plugin_id: str,
        *,
        permissions: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/ecosystem/plugins/install",
            body={"source": plugin_id, "permissions": permissions, "config": config},
        )

    def uninstall_plugin(self, plugin_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/ecosystem/plugins/{plugin_id}")

    def enable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/ecosystem/plugins/{plugin_id}/enable")

    def disable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/ecosystem/plugins/{plugin_id}/disable")

    def invoke_plugin(
        self, plugin_id: str, method: str, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/ecosystem/plugins/{plugin_id}/invoke",
            body={"method": method, "args": list(args), "kwargs": kwargs},
        )

    # ---------------- API keys ----------------

    def create_api_key(
        self, label: str, scopes: Iterable[str], tier: str = "authenticated"
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/ecosystem/api/keys",
            body={"label": label, "scopes": list(scopes), "tier": tier},
        )

    def revoke_api_key(self, key_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/ecosystem/api/keys/{key_id}")

    def analytics(self) -> Dict[str, Any]:
        return self._request("GET", "/ecosystem/api/analytics")

    # ---------------- Webhooks ----------------

    def create_webhook(
        self,
        url: str,
        events: Iterable[str],
        *,
        description: str = "",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/ecosystem/webhooks/subscriptions",
            body={"url": url, "events": list(events), "description": description, "filters": filters},
        )

    def list_webhooks(self) -> Dict[str, Any]:
        return self._request("GET", "/ecosystem/webhooks/subscriptions")

    def delete_webhook(self, sub_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/ecosystem/webhooks/subscriptions/{sub_id}")

    # ---------------- Integrations ----------------

    def list_integrations_catalog(self) -> Dict[str, Any]:
        return self._request("GET", "/ecosystem/integrations/catalog")

    def connect_integration(
        self,
        provider: str,
        label: str,
        *,
        scopes: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/ecosystem/integrations/connections",
            body={
                "provider": provider,
                "label": label,
                "scopes": scopes,
                "config": config,
                "access_token": access_token,
            },
        )

    def integration_action(
        self, connection_id: str, action: str, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/ecosystem/integrations/connections/{connection_id}/invoke",
            body={"action": action, "args": list(args), "kwargs": kwargs},
        )

    # ---------------- Marketplace ----------------

    def marketplace_search(
        self,
        *,
        q: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        sort: str = "popular",
    ) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/ecosystem/marketplace/listings",
            params={"q": q, "category": category, "tag": tag, "sort": sort},
        )

    def marketplace_install(
        self,
        listing_id: str,
        *,
        permissions: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/ecosystem/marketplace/listings/{listing_id}/install",
            body={"permissions": permissions, "config": config},
        )

    # ---------------- Webhook signature helpers ----------------

    @staticmethod
    def sign_payload(payload: bytes, secret: str, *, timestamp: Optional[int] = None) -> str:
        ts = timestamp or int(time.time())
        mac = hmac.new(secret.encode("utf-8"), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
        return f"t={ts},v1={mac}"

    @staticmethod
    def verify_payload(
        payload: bytes,
        signature: str,
        secret: str,
        *,
        tolerance_seconds: int = 300,
    ) -> bool:
        if not signature:
            return False
        parts = dict(p.split("=", 1) for p in signature.split(",") if "=" in p)
        ts_raw = parts.get("t")
        sig = parts.get("v1")
        if not ts_raw or not sig:
            return False
        try:
            ts = int(ts_raw)
        except ValueError:
            return False
        if abs(time.time() - ts) > tolerance_seconds:
            return False
        expected = hmac.new(
            secret.encode("utf-8"),
            f"{ts}.".encode() + payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, sig)


@dataclass
class AsyncAstrovoxClient:
    """Async version of :class:`AstrovoxClient` using ``httpx``.

    Importing this class requires ``httpx``; the synchronous client above
    does not.
    """

    base_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    timeout: float = 30.0

    def _headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "astrovox-python-sdk/1.0", "Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
            if self.api_secret:
                headers["X-API-Secret"] = self.api_secret
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        import httpx

        url = urllib.parse.urljoin(self.base_url + "/", path.lstrip("/"))
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                json=body,
                headers=self._headers(),
            )
            if response.status_code >= 400:
                raise AstrovoxError(
                    response.text,
                    status=response.status_code,
                    payload=response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
                )
            return response.json()

    async def chat(self, messages: List[Dict[str, str]], **options: Any) -> Dict[str, Any]:
        return await self._request("POST", "/v1/chat/completions", {"messages": messages, **options})

    async def list_plugins(self) -> Dict[str, Any]:
        return await self._request("GET", "/ecosystem/plugins")

    async def invoke_plugin(self, plugin_id: str, method: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return await self._request(
            "POST",
            f"/ecosystem/plugins/{plugin_id}/invoke",
            {"method": method, "args": list(args), "kwargs": kwargs},
        )