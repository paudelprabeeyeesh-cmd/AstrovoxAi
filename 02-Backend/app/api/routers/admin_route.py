"""Admin API routes — governance, billing, compliance, support, partners."""

from fastapi import APIRouter, HTTPException, status, Depends, Header, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.cost_management import cost_tracker
from app.compliance import compliance_manager
from app.enterprise_audit import export_audit_logs
from ..retention import retention_engine
from app.billing_meter import billing_meter
from app.usage_quota import usage_quota_manager
from app.iam import require_admin, Principal
from app.middleware.security.security_hardening import get_audit_log

router = APIRouter(prefix="/api/admin", tags=["admin"])
_audit = get_audit_log()


# ============================================================================
# Governance
# ============================================================================


class TenantConfigRequest(BaseModel):
    name: str
    plan: str = "free"
    data_residency: str = "default"


@router.post("/tenants")
async def create_tenant(request: TenantConfigRequest, principal: Principal = Depends(require_admin)):
    from app.multi_tenancy import tenant_manager
    tenant = tenant_manager.create_tenant(
        tenant_id=str(uuid.uuid4()),
        name=request.name,
        plan=request.plan,
        data_residency=request.data_residency,
    )
    _audit.record(actor=principal.id, action="admin_create_tenant", target="tenants", outcome="success")
    return {"status": "OK", "tenant": {"tenant_id": tenant.tenant_id, "name": tenant.name, "plan": tenant.plan}}


@router.get("/tenants")
async def list_tenants(principal: Principal = Depends(require_admin)):
    from app.multi_tenancy import tenant_manager
    _audit.record(actor=principal.id, action="admin_list_tenants", target="tenants", outcome="success")
    return {"status": "OK", "tenants": tenant_manager.list_tenants()}


# ============================================================================
# Audit Log Exporter
# ============================================================================


class AuditExportRequest(BaseModel):
    format: str = "json"
    filters: Dict[str, Any] = Field(default_factory=dict)


@router.post("/audit/export")
async def export_audit(request: AuditExportRequest, principal: Principal = Depends(require_admin)):
    _audit.record(actor=principal.id, action="admin_audit_export", target="audit", outcome="success")
    result = export_audit_logs(requester_id=principal.id, format=request.format, filters=request.filters)
    return {"status": "OK", **result}


@router.get("/audit/logs")
async def get_audit_logs(principal: Principal = Depends(require_admin), limit: int = Query(100, ge=1, le=1000)):
    from app.audit import get_audit_log as _get_audit_log
    logs = _get_audit_log(principal.id, limit)
    _audit.record(actor=principal.id, action="admin_audit_list", target="audit", outcome="success")
    return {"status": "OK", "logs": logs}


# ============================================================================
# Retention Policy Engine
# ============================================================================


class RetentionPolicyRequest(BaseModel):
    name: str
    data_type: str
    retention_days: int
    action: str = "delete"


@router.post("/retention/policies")
async def create_retention_policy(request: RetentionPolicyRequest, principal: Principal = Depends(require_admin)):
    policy = retention_engine.create_policy(
        name=request.name,
        data_type=request.data_type,
        retention_days=request.retention_days,
        action=request.action,
    )
    _audit.record(actor=principal.id, action="admin_create_retention_policy", target="retention", outcome="success")
    return {"status": "OK", "policy": {"id": policy.id, "name": policy.name, "data_type": policy.data_type}}


@router.get("/retention/policies")
async def list_retention_policies(principal: Principal = Depends(require_admin)):
    _audit.record(actor=principal.id, action="admin_list_retention_policies", target="retention", outcome="success")
    return {"status": "OK", "policies": retention_engine.list_policies()}


@router.post("/retention/enforce")
async def enforce_retention(data_type: str, principal: Principal = Depends(require_admin)):
    _audit.record(actor=principal.id, action="admin_enforce_retention", target="retention", outcome="success")
    result = retention_engine.enforce_retention(data_type)
    return {"status": "OK", **result}


# ============================================================================
# Billing Metering
# ============================================================================


@router.get("/billing/usage")
async def get_billing_usage(tenant_id: str, principal: Principal = Depends(require_admin)):
    _audit.record(actor=principal.id, action="admin_billing_usage", target="billing", outcome="success")
    usage = billing_meter.get_tenant_usage(tenant_id)
    return {"status": "OK", "usage": usage}


@router.get("/billing/summary")
async def get_billing_summary(tenant_id: str, period: str = "monthly", principal: Principal = Depends(require_admin)):
    _audit.record(actor=principal.id, action="admin_billing_summary", target="billing", outcome="success")
    summary = billing_meter.get_tenant_cost_summary(tenant_id, period)
    return {"status": "OK", "summary": summary}


# ============================================================================
# Usage Quotas
# ============================================================================


class QuotaRequest(BaseModel):
    tenant_id: str
    user_id: str
    resource_type: str
    limit_value: float
    period: str = "monthly"


@router.post("/quotas")
async def create_quota(request: QuotaRequest, principal: Principal = Depends(require_admin)):
    quota = usage_quota_manager.create_quota(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        resource_type=request.resource_type,
        limit_value=request.limit_value,
        period=request.period,
    )
    _audit.record(actor=principal.id, action="admin_create_quota", target="quotas", outcome="success")
    return {"status": "OK", "quota": {"id": quota.id, "tenant_id": quota.tenant_id, "resource_type": quota.resource_type}}


@router.get("/quotas")
async def list_quotas(tenant_id: Optional[str] = None, principal: Principal = Depends(require_admin)):
    _audit.record(actor=principal.id, action="admin_list_quotas", target="quotas", outcome="success")
    quotas = usage_quota_manager.list_quotas(tenant_id)
    return {"status": "OK", "quotas": quotas}


@router.get("/quotas/check")
async def check_quota(tenant_id: str, user_id: str, resource_type: str, quantity: float = 1.0, principal: Principal = Depends(require_admin)):
    _audit.record(actor=principal.id, action="admin_check_quota", target="quotas", outcome="success")
    result = usage_quota_manager.check_quota(tenant_id, user_id, resource_type, quantity)
    return {"status": "OK", **result}


# ============================================================================
# Support Tickets
# ============================================================================


class SupportTicketRequest(BaseModel):
    tenant_id: str
    user_id: str
    subject: str
    description: str
    priority: str = "medium"
    category: str = "general"
    tags: List[str] = Field(default_factory=list)


@router.post("/support/tickets")
async def create_support_ticket(request: SupportTicketRequest, principal: Principal = Depends(require_admin)):
    from app.support import support_ticket_service
    ticket = support_ticket_service.create_ticket(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        subject=request.subject,
        description=request.description,
        priority=request.priority,
        category=request.category,
        tags=request.tags,
    )
    _audit.record(actor=principal.id, action="admin_create_support_ticket", target="support", outcome="success")
    return {"status": "OK", "ticket": {"id": ticket.id, "subject": ticket.subject, "status": ticket.status}}


@router.get("/support/tickets")
async def list_support_tickets(tenant_id: Optional[str] = None, status: Optional[str] = None, principal: Principal = Depends(require_admin)):
    from app.support import support_ticket_service
    _audit.record(actor=principal.id, action="admin_list_support_tickets", target="support", outcome="success")
    tickets = support_ticket_service.list_tickets(tenant_id=tenant_id, status=status)
    return {"status": "OK", "tickets": [{"id": t.id, "subject": t.subject, "status": t.status, "priority": t.priority} for t in tickets]}


@router.patch("/support/tickets/{ticket_id}")
async def update_support_ticket(ticket_id: str, status: Optional[str] = None, assigned_to: Optional[str] = None, principal: Principal = Depends(require_admin)):
    from app.support import support_ticket_service
    _audit.record(actor=principal.id, action="admin_update_support_ticket", target="support", outcome="success")
    ticket = support_ticket_service.update_ticket(ticket_id, status=status, assigned_to=assigned_to)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "OK", "ticket": {"id": ticket.id, "status": ticket.status}}


# ============================================================================
# Partner/Ecosystem APIs
# ============================================================================


class PartnerAccountRequest(BaseModel):
    tenant_id: str
    name: str
    scopes: List[str] = Field(default_factory=list)


@router.post("/partners")
async def create_partner(request: PartnerAccountRequest, principal: Principal = Depends(require_admin)):
    from app.partners import partner_service
    account = partner_service.create_partner(
        tenant_id=request.tenant_id,
        name=request.name,
        scopes=request.scopes,
    )
    _audit.record(actor=principal.id, action="admin_create_partner", target="partners", outcome="success")
    return {"status": "OK", "partner": {"id": account.id, "name": account.name, "api_key": account.api_key}}


@router.get("/partners")
async def list_partners(tenant_id: Optional[str] = None, principal: Principal = Depends(require_admin)):
    from app.partners import partner_service
    _audit.record(actor=principal.id, action="admin_list_partners", target="partners", outcome="success")
    accounts = partner_service.list_partners(tenant_id=tenant_id)
    return {"status": "OK", "partners": [{"id": a.id, "name": a.name, "is_active": a.is_active} for a in accounts]}


# ============================================================================
# Export/Import Workflows
# ============================================================================


class ExportImportRequest(BaseModel):
    tenant_id: str
    job_type: str
    resource_type: str
    format: str = "json"
    filters: Dict[str, Any] = Field(default_factory=dict)


@router.post("/export-import/export")
async def create_export_job(request: ExportImportRequest, principal: Principal = Depends(require_admin)):
    from app.export_import import export_import_service
    job = export_import_service.create_export_job(
        tenant_id=request.tenant_id,
        resource_type=request.resource_type,
        format=request.format,
        filters=request.filters,
        created_by=principal.id,
    )
    _audit.record(actor=principal.id, action="admin_create_export", target="export_import", outcome="success")
    return {"status": "OK", "job": {"id": job.id, "job_type": job.job_type, "status": job.status}}


@router.post("/export-import/import")
async def create_import_job(request: ExportImportRequest, principal: Principal = Depends(require_admin)):
    from app.export_import import export_import_service
    job = export_import_service.create_import_job(
        tenant_id=request.tenant_id,
        resource_type=request.resource_type,
        format=request.format,
        filters=request.filters,
        created_by=principal.id,
    )
    _audit.record(actor=principal.id, action="admin_create_import", target="export_import", outcome="success")
    return {"status": "OK", "job": {"id": job.id, "job_type": job.job_type, "status": job.status}}


@router.get("/export-import/jobs")
async def list_export_import_jobs(tenant_id: Optional[str] = None, principal: Principal = Depends(require_admin)):
    from app.export_import import export_import_service
    _audit.record(actor=principal.id, action="admin_list_export_import_jobs", target="export_import", outcome="success")
    jobs = export_import_service.list_jobs(tenant_id=tenant_id)
    return {"status": "OK", "jobs": [{"id": j.id, "job_type": j.job_type, "status": j.status} for j in jobs]}
