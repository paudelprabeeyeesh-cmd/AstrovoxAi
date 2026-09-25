"""Admin dashboard APIs."""

from fastapi import APIRouter, HTTPException, status, Header, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.utils.auth.auth_utils import get_user_id_from_token
from .dashboard import admin_dashboard
from .tenancy import tenant_manager
from .audit import audit_exporter
from .retention import retention_engine
from .compliance import compliance_generator
from .export_import import export_import_service
from .partners import partner_service
from .sso import enterprise_sso

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard/overview")
async def get_dashboard_overview(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "overview": {
            "tenants": admin_dashboard.list_all_tenants(),
            "health": admin_dashboard.get_system_health(),
        },
    }


@router.get("/dashboard/tenants/{tenant_id}")
async def get_tenant_dashboard(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    overview = admin_dashboard.get_tenant_overview(tenant_id)
    if "error" in overview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=overview["error"])
    audit = admin_dashboard.get_audit_summary(tenant_id)
    compliance = admin_dashboard.get_compliance_status(tenant_id)
    billing = admin_dashboard.get_billing_summary(tenant_id)
    partners = admin_dashboard.get_partner_activity(tenant_id)
    sso = admin_dashboard.get_sso_status(tenant_id)
    return {
        "status": "OK",
        "tenant": overview,
        "audit_summary": audit,
        "compliance_status": compliance,
        "billing_summary": billing,
        "partners": partners,
        "sso_status": sso,
    }


@router.get("/dashboard/tenants/{tenant_id}/audit")
async def get_tenant_audit(tenant_id: str, authorization: str = Header(None), days: int = Query(7, ge=1, le=90)):
    user_id = get_user_id_from_token(authorization)
    result = admin_dashboard.get_audit_summary(tenant_id, days)
    return {"status": "OK", "audit_summary": result}


@router.get("/dashboard/tenants/{tenant_id}/compliance")
async def get_tenant_compliance(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    result = admin_dashboard.get_compliance_status(tenant_id)
    return {"status": "OK", "compliance": result}


@router.get("/dashboard/tenants/{tenant_id}/billing")
async def get_tenant_billing(tenant_id: str, authorization: str = Header(None), period: str = Query("monthly")):
    user_id = get_user_id_from_token(authorization)
    result = admin_dashboard.get_billing_summary(tenant_id, period)
    return {"status": "OK", "billing": result}


@router.get("/dashboard/tenants/{tenant_id}/partners")
async def get_tenant_partners(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    partners = admin_dashboard.get_partner_activity(tenant_id)
    return {"status": "OK", "partners": partners}


@router.get("/dashboard/tenants/{tenant_id}/sso")
async def get_tenant_sso(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    sso = admin_dashboard.get_sso_status(tenant_id)
    return {"status": "OK", "sso": sso}


@router.get("/dashboard/retention")
async def get_retention_dashboard(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    result = admin_dashboard.get_retention_status()
    return {"status": "OK", "retention": result}


@router.get("/dashboard/export-import")
async def get_export_import_dashboard(tenant_id: Optional[str] = Query(None), authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    jobs = export_import_service.list_jobs(tenant_id=tenant_id)
    return {
        "status": "OK",
        "jobs": [
            {
                "id": j.id,
                "job_type": j.job_type,
                "resource_type": j.resource_type,
                "status": j.status,
                "created_at": j.created_at,
            }
            for j in jobs
        ],
    }
