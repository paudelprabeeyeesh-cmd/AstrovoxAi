"""Tenant isolation middleware."""

import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from .tenancy import tenant_manager

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("x-tenant-id") or tenant_manager.get_default_tenant_id()
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID required")
        tenant = tenant_manager.get_tenant(tenant_id)
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=403, detail="Tenant not found or inactive")
        request.state.tenant_id = tenant_id
        request.state.tenant = tenant
        response = await call_next(request)
        return response
