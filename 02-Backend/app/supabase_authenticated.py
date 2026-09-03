"""
Per-request authenticated Supabase client factory.

Replaces the global anon-key Supabase client with per-request clients
that use the caller's JWT. This makes Supabase Row Level Security (RLS)
actually enforce tenant isolation.

Usage:
    from app.iam import get_current_principal
    from app.supabase_authenticated import get_supabase

    @router.get("/conversations")
    async def list_conversations(principal = Depends(get_current_principal)):
        supabase = get_supabase(principal)
        result = supabase.table("conversations").select("*").execute()
        ...
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .iam import get_jwt_secret
from .security_hardening import Principal


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


class SupabaseClient:
    """Minimal per-request Supabase client.

    In production this wraps the official `supabase` library. The
    implementation here is intentionally lightweight so the security
    module can be unit-tested without requiring a live Supabase
    project.
    """

    def __init__(self, url: str, key: str, *, jwt: Optional[str] = None) -> None:
        self.url = url
        self.key = key
        self.jwt = jwt
        self._headers: Dict[str, str] = {
            "apikey": key,
            "Content-Type": "application/json",
        }
        if jwt:
            self._headers["Authorization"] = f"Bearer {jwt}"

    def table(self, name: str) -> "SupabaseTable":
        return SupabaseTable(self, name)

    def rpc(self, name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        raise NotImplementedError("RPC calls are not supported in the mock client")

    @property
    def headers(self) -> Dict[str, str]:
        return dict(self._headers)


class SupabaseTable:
    """Fluent query builder that emits REST-style filter strings."""

    def __init__(self, client: SupabaseClient, name: str) -> None:
        self.client = client
        self.name = name
        self._filters: list = []
        self._select: str = "*"
        self._limit: Optional[int] = None
        self._order: Optional[str] = None

    def select(self, columns: str = "*") -> "SupabaseTable":
        self._select = columns
        return self

    def eq(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append(f"{column}=eq.{value}")
        return self

    def neq(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append(f"{column}=neq.{value}")
        return self

    def in_(self, column: str, values: List[Any]) -> "SupabaseTable":
        joined = ",".join(str(v) for v in values)
        self._filters.append(f"{column}=in.({joined})")
        return self

    def gte(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append(f"{column}=gte.{value}")
        return self

    def lte(self, column: str, value: Any) -> "SupabaseTable":
        self._filters.append(f"{column}=lte.{value}")
        return self

    def like(self, column: str, pattern: str) -> "SupabaseTable":
        self._filters.append(f"{column}=like.{pattern}")
        return self

    def limit(self, count: int) -> "SupabaseTable":
        self._limit = count
        return self

    def order(self, column: str, *, desc: bool = False) -> "SupabaseTable":
        self._order = f"{column}.{'desc' if desc else 'asc'}"
        return self

    def _build_url(self) -> str:
        url = f"{self.client.url}/rest/v1/{self.name}"
        params: list = []
        if self._select and self._select != "*":
            params.append(("select", self._select))
        for f in self._filters:
            # Each filter is already in PostgREST syntax (key=op.value)
            key, value = f.split("=", 1)
            params.append((key, value))
        if self._order:
            params.append(("order", self._order))
        if self._limit is not None:
            params.append(("limit", str(self._limit)))
        if params:
            from urllib.parse import urlencode

            url = f"{url}?{urlencode(params)}"
        return url

    def execute(self) -> Dict[str, Any]:
        """Execute the query.

        In production this would issue an HTTP request with the
        per-request JWT. In tests / local dev this returns an empty
        result so the calling code can be exercised.
        """
        url = self._build_url()
        try:
            import httpx

            resp = httpx.get(
                url,
                headers=self.client.headers,
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return {"data": data, "count": len(data)}
                return data
            return {
                "data": [],
                "count": 0,
                "error": resp.text,
            }
        except Exception as exc:
            return {"data": [], "count": 0, "error": str(exc)}

    def insert(self, row: Dict[str, Any]) -> "SupabaseMutation":
        return SupabaseMutation(self.client, self.name, "POST", [row])

    def update(self, row: Dict[str, Any]) -> "SupabaseMutation":
        return SupabaseMutation(self.client, self.name, "PATCH", [row], filters=self._filters)

    def delete(self) -> "SupabaseMutation":
        return SupabaseMutation(self.client, self.name, "DELETE", filters=self._filters)


class SupabaseMutation:
    def __init__(
        self,
        client: SupabaseClient,
        table: str,
        method: str,
        rows: Optional[List[Dict[str, Any]]] = None,
        filters: Optional[list] = None,
    ) -> None:
        self.client = client
        self.table = table
        self.method = method
        self.rows = rows or []
        self.filters = filters or []

    def _url(self) -> str:
        url = f"{self.client.url}/rest/v1/{self.table}"
        if self.filters:
            from urllib.parse import urlencode

            url = f"{url}?{urlencode(self.filters)}"
        return url

    def execute(self) -> Dict[str, Any]:
        url = self._url()
        try:
            import httpx

            if self.method == "POST":
                resp = httpx.post(
                    url,
                    headers={**self.client.headers, "Prefer": "return=representation"},
                    json=self.rows,
                    timeout=10.0,
                )
            elif self.method == "PATCH":
                resp = httpx.patch(
                    url,
                    headers=self.client.headers,
                    json=self.rows[0] if self.rows else {},
                    timeout=10.0,
                )
            elif self.method == "DELETE":
                resp = httpx.delete(
                    url,
                    headers=self.client.headers,
                    timeout=10.0,
                )
            else:
                return {"data": None, "error": "unsupported method"}
            if resp.status_code in (200, 201):
                data = resp.json() if resp.text else None
                if isinstance(data, list):
                    return {"data": data, "count": len(data)}
                return {"data": data, "count": 1 if data else 0}
            return {
                "data": None,
                "error": resp.text,
                "status": resp.status_code,
            }
        except Exception as exc:
            return {"data": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_supabase(principal: Principal, *, service: bool = False) -> SupabaseClient:
    """Create a Supabase client scoped to the calling principal.

    The JWT from the principal is forwarded as the Authorization header.
    This is what allows Supabase Row Level Security to enforce tenant
    isolation.
    """
    if service:
        if not SUPABASE_SERVICE_KEY:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured")
        return SupabaseClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase URL or anon key not configured")

    return SupabaseClient(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        jwt=principal.raw_claims.get("token") if principal.raw_claims else None,
    )


def get_anonymous_supabase() -> SupabaseClient:
    """Build a Supabase client with no JWT (public access only).

    Use sparingly — most operations should go through `get_supabase(principal)`.
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase URL or anon key not configured")
    return SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY)
