"""Enterprise API endpoints — organizations, workspaces, memberships, tenancy, ABAC, audit, compliance."""

from fastapi import APIRouter, Header, HTTPException, status, Request, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.utils.auth.auth_utils import get_user_id_from_token
from .service import org_service
from .rbac import rbac
from .abac import abac, ABACContext
from .tenancy import tenant_manager, tenant_required, tenant_scoped
from .encryption import tenant_encryption
from .audit import audit_exporter
from .compliance import compliance_generator
from .models import ORG_ROLES, WORKSPACE_ROLES

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])


# ============================================================================
# Request Models
# ============================================================================

class CreateOrgRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    website: Optional[str] = ""


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None


class CreateWorkspaceRequest(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = ""
    type: Optional[str] = "team"


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class InviteMemberRequest(BaseModel):
    user_id: str
    role: Optional[str] = "member"


class UpdateRoleRequest(BaseModel):
    role: str


class TenantCreateRequest(BaseModel):
    tenant_id: str
    name: str
    plan: Optional[str] = "free"
    data_residency: Optional[str] = "default"


class TenantUpdateRequest(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    data_residency: Optional[str] = None
    is_active: Optional[bool] = None


class ABACPolicyRequest(BaseModel):
    name: str
    effect: str
    conditions: Dict[str, Any]


class AuditExportRequest(BaseModel):
    format: Optional[str] = "json"
    filters: Optional[Dict[str, Any]] = None


class ComplianceReportRequest(BaseModel):
    tenant_id: str
    framework: str
    period_start: str
    period_end: str


class EncryptRequest(BaseModel):
    plaintext: str


class TenantResidencyRequest(BaseModel):
    tenant_id: str
    data_residency: str


# ============================================================================
# Organizations
# ============================================================================

@router.post("/organizations")
async def create_organization(request: CreateOrgRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    org, membership = org_service.create_organization(
        name=request.name,
        owner_id=user_id,
        description=request.description or "",
        website=request.website or "",
    )
    return {
        "status": "OK",
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "description": org.description,
            "owner_id": org.owner_id,
            "created_at": org.created_at,
        },
        "role": membership.role,
    }


@router.get("/organizations")
async def list_organizations(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    orgs = org_service.get_user_organizations(user_id)
    return {
        "status": "OK",
        "organizations": [
            {
                "id": o.id,
                "name": o.name,
                "slug": o.slug,
                "member_count": o.member_count,
                "workspace_count": o.workspace_count,
                "role": rbac.get_org_role(user_id, o.id),
            }
            for o in orgs
        ],
    }


@router.get("/organizations/{org_id}")
async def get_organization(org_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_org_permission(user_id, org_id, "org:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    org = org_service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return {
        "status": "OK",
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "description": org.description,
            "website": org.website,
            "owner_id": org.owner_id,
            "member_count": org.member_count,
            "workspace_count": org.workspace_count,
            "created_at": org.created_at,
            "role": rbac.get_org_role(user_id, org.id),
        },
    }


@router.patch("/organizations/{org_id}")
async def update_organization(org_id: str, request: UpdateOrgRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_org_permission(user_id, org_id, "org:write"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    org = org_service.update_organization(org_id, name=request.name, description=request.description, website=request.website)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return {"status": "OK", "organization": {"id": org.id, "name": org.name, "slug": org.slug}}


@router.delete("/organizations/{org_id}")
async def delete_organization(org_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_org_permission(user_id, org_id, "org:delete"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not org_service.delete_organization(org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return {"status": "OK", "message": "Organization deleted"}


# ============================================================================
# Organization Members
# ============================================================================

@router.post("/organizations/{org_id}/members")
async def invite_member(org_id: str, request: InviteMemberRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_org_permission(user_id, org_id, "member:invite"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    membership = org_service.add_member(org_id, request.user_id, request.role, user_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to add member")
    return {
        "status": "OK",
        "membership": {
            "id": membership.id,
            "user_id": membership.user_id,
            "role": membership.role,
            "status": membership.status,
        },
    }


@router.get("/organizations/{org_id}/members")
async def list_members(org_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_org_permission(user_id, org_id, "org:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    members = org_service.list_members(org_id)
    return {
        "status": "OK",
        "members": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "role": m.role,
                "status": m.status,
                "joined_at": m.joined_at,
            }
            for m in members
        ],
    }


@router.patch("/organizations/{org_id}/members/{member_user_id}")
async def update_member_role(org_id: str, member_user_id: str, request: UpdateRoleRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.can_manage_member(user_id, member_user_id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot manage this member")
    membership = org_service.update_member_role(org_id, member_user_id, request.role)
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update role")
    return {"status": "OK", "role": membership.role}


@router.delete("/organizations/{org_id}/members/{member_user_id}")
async def remove_member(org_id: str, member_user_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.can_manage_member(user_id, member_user_id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot remove this member")
    if not org_service.remove_member(org_id, member_user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return {"status": "OK", "message": "Member removed"}


# ============================================================================
# Workspaces
# ============================================================================

@router.post("/workspaces")
async def create_workspace(request: CreateWorkspaceRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_org_permission(user_id, request.organization_id, "workspace:create"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    ws, membership = org_service.create_workspace(
        organization_id=request.organization_id,
        name=request.name,
        owner_id=user_id,
        description=request.description or "",
        ws_type=request.type or "team",
    )
    return {
        "status": "OK",
        "workspace": {
            "id": ws.id,
            "name": ws.name,
            "slug": ws.slug,
            "type": ws.type,
            "organization_id": ws.organization_id,
            "created_at": ws.created_at,
        },
        "role": membership.role,
    }


@router.get("/organizations/{org_id}/workspaces")
async def list_workspaces(org_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_org_permission(user_id, org_id, "org:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    workspaces = org_service.get_user_workspaces(user_id, org_id)
    return {
        "status": "OK",
        "workspaces": [
            {
                "id": w.id,
                "name": w.name,
                "slug": w.slug,
                "type": w.type,
                "member_count": w.member_count,
                "role": rbac.get_workspace_role(user_id, w.id),
            }
            for w in workspaces
        ],
    }


@router.get("/workspaces/{ws_id}")
async def get_workspace(ws_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, ws_id, "workspace:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    ws = org_service.get_workspace(ws_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {
        "status": "OK",
        "workspace": {
            "id": ws.id,
            "name": ws.name,
            "slug": ws.slug,
            "description": ws.description,
            "type": ws.type,
            "organization_id": ws.organization_id,
            "member_count": ws.member_count,
            "role": rbac.get_workspace_role(user_id, ws.id),
        },
    }


@router.patch("/workspaces/{ws_id}")
async def update_workspace(ws_id: str, request: UpdateWorkspaceRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, ws_id, "workspace:write"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    ws = org_service.update_workspace(ws_id, name=request.name, description=request.description)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {"status": "OK", "workspace": {"id": ws.id, "name": ws.name}}


@router.post("/workspaces/{ws_id}/archive")
async def archive_workspace(ws_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, ws_id, "workspace:delete"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not org_service.archive_workspace(ws_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {"status": "OK", "message": "Workspace archived"}


# ============================================================================
# Workspace Members
# ============================================================================

@router.post("/workspaces/{ws_id}/members")
async def add_workspace_member(ws_id: str, request: InviteMemberRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, ws_id, "member:invite"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    membership = org_service.add_workspace_member(ws_id, request.user_id, request.role)
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to add member")
    return {
        "status": "OK",
        "membership": {
            "id": membership.id,
            "user_id": membership.user_id,
            "role": membership.role,
            "status": membership.status,
        },
    }


@router.get("/workspaces/{ws_id}/members")
async def list_workspace_members(ws_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, ws_id, "workspace:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    members = org_service.list_workspace_members(ws_id)
    return {
        "status": "OK",
        "members": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "role": m.role,
                "status": m.status,
                "joined_at": m.joined_at,
            }
            for m in members
        ],
    }


@router.patch("/workspaces/{ws_id}/members/{member_user_id}")
async def update_workspace_member_role(ws_id: str, member_user_id: str, request: UpdateRoleRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, ws_id, "member:manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    membership = org_service.update_workspace_member_role(ws_id, member_user_id, request.role)
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update role")
    return {"status": "OK", "role": membership.role}


@router.delete("/workspaces/{ws_id}/members/{member_user_id}")
async def remove_workspace_member(ws_id: str, member_user_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, ws_id, "member:remove"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not org_service.remove_workspace_member(ws_id, member_user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return {"status": "OK", "message": "Member removed"}


# ============================================================================
# Roles
# ============================================================================

@router.get("/roles/organization")
async def list_org_roles(authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "roles": [
            {"name": name, "description": data["description"], "permissions": data["permissions"]}
            for name, data in ORG_ROLES.items()
        ],
    }


@router.get("/roles/workspace")
async def list_workspace_roles(authorization: str = Header(None)):
    get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "roles": [
            {"name": name, "description": data["description"], "permissions": data["permissions"]}
            for name, data in WORKSPACE_ROLES.items()
        ],
    }


# ============================================================================
# Multi-Tenancy
# ============================================================================

@router.post("/tenants")
async def create_tenant(request: TenantCreateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    tenant = tenant_manager.create_tenant(
        tenant_id=request.tenant_id,
        name=request.name,
        plan=request.plan or "free",
        data_residency=request.data_residency or "default",
    )
    return {
        "status": "OK",
        "tenant": {
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "plan": tenant.plan,
            "data_residency": tenant.data_residency,
        },
    }


@router.get("/tenants")
async def list_tenants(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "tenants": tenant_manager.list_tenants()}


@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    tenant = tenant_manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return {
        "status": "OK",
        "tenant": {
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "plan": tenant.plan,
            "is_active": tenant.is_active,
            "data_residency": tenant.data_residency,
            "created_at": tenant.created_at,
        },
    }


@router.patch("/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, request: TenantUpdateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    tenant = tenant_manager.update_tenant(
        tenant_id,
        name=request.name,
        plan=request.plan,
        data_residency=request.data_residency,
        is_active=request.is_active,
    )
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return {"status": "OK", "tenant": {"tenant_id": tenant.tenant_id, "name": tenant.name}}


@router.delete("/tenants/{tenant_id}")
async def deactivate_tenant(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not tenant_manager.deactivate_tenant(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return {"status": "OK", "message": "Tenant deactivated"}


@router.post("/tenants/{tenant_id}/rotate-key")
async def rotate_tenant_key(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    key = tenant_encryption.rotate_key(tenant_id)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return {"status": "OK", "key_id": key.key_id, "is_active": key.is_active}


# ============================================================================
# Data Residency
# ============================================================================

@router.get("/tenants/{tenant_id}/residency")
async def get_tenant_residency(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    config = tenant_manager.get_residency_config(tenant_id)
    return {"status": "OK", "tenant_id": tenant_id, "residency": config}


@router.post("/tenants/residency")
async def set_tenant_residency(request: TenantResidencyRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    tenant = tenant_manager.update_tenant(request.tenant_id, data_residency=request.data_residency)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return {"status": "OK", "tenant_id": request.tenant_id, "data_residency": request.data_residency}


# ============================================================================
# ABAC Policies
# ============================================================================

@router.post("/abac/policies")
async def create_abac_policy(request: ABACPolicyRequest, authorization: str = Header(None)):
    abac.add_policy({
        "name": request.name,
        "effect": request.effect,
        "conditions": request.conditions,
    })
    return {"status": "OK", "message": "ABAC policy added", "name": request.name}


@router.get("/abac/policies")
async def list_abac_policies(authorization: str = Header(None)):
    return {"status": "OK", "policies": abac._policies}


# ============================================================================
# Audit Log Exporter
# ============================================================================

@router.post("/audit/export")
async def export_audit_logs(request: AuditExportRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    result = audit_exporter.export(requester_id=user_id, format=request.format or "json", filters=request.filters)
    return {"status": "OK", **result}


@router.get("/audit/logs")
async def get_audit_logs(authorization: str = Header(None), limit: int = 100):
    user_id = get_user_id_from_token(authorization)
    logs = audit_exporter.list_logs(user_id, limit)
    return {"status": "OK", "logs": logs}


@router.get("/audit/tamper-check")
async def check_tamper(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    logs = audit_exporter.list_logs(user_id, 1000)
    from .audit import TamperEvidenceChain, AuditLog
    chain = TamperEvidenceChain()
    audit_objs = [
        AuditLog(
            log_id=l.get("id", ""),
            actor_id=l.get("user_id", ""),
            action=l.get("action", ""),
            target="",
            outcome="",
            metadata=json.loads(l.get("metadata") or "{}"),
            created_at=datetime.fromisoformat(l["created_at"]).timestamp() if l.get("created_at") else 0,
            chain_hash=l.get("chain_hash", ""),
        )
        for l in logs
    ]
    result = chain.verify_chain(audit_objs)
    return {"status": "OK", "tamper_check": result}


# ============================================================================
# Compliance Report Generator
# ============================================================================

@router.post("/compliance/reports")
async def generate_compliance_report(request: ComplianceReportRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    start_date = datetime.fromisoformat(request.period_start)
    end_date = datetime.fromisoformat(request.period_end)
    report = compliance_generator.generate(request.tenant_id, request.framework, start_date, end_date)
    return {
        "status": "OK",
        "report": {
            "report_id": report.report_id,
            "tenant_id": report.tenant_id,
            "framework": report.framework,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "summary": report.summary,
        },
    }


@router.get("/compliance/reports/{report_id}")
async def get_compliance_report(report_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    report = compliance_generator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    export_data = compliance_generator.export_report(report, fmt="json")
    return {"status": "OK", "report": json.loads(export_data)}


# ============================================================================
# Tenant Encryption
# ============================================================================

@router.post("/tenants/{tenant_id}/encrypt")
async def encrypt_tenant_data(tenant_id: str, request: EncryptRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    ciphertext = tenant_encryption.encrypt(tenant_id, request.plaintext)
    return {"status": "OK", "ciphertext": ciphertext}


@router.post("/tenants/{tenant_id}/decrypt")
async def decrypt_tenant_data(tenant_id: str, request: EncryptRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    plaintext = tenant_encryption.decrypt(tenant_id, request.plaintext)
    return {"status": "OK", "plaintext": plaintext}


@router.get("/tenants/{tenant_id}/encryption/key")
async def get_tenant_key_info(tenant_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    info = tenant_encryption.get_key_info(tenant_id)
    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return {"status": "OK", "key_info": info}
