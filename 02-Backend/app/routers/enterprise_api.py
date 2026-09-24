
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from .auth import get_current_user
from .database import get_db
from .audit import log_action

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class OrganizationCreate(BaseModel):
    name: str
    plan: str = "free"
    slug: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    owner_id: str
    plan: str
    tenant_id: Optional[str]
    status: str
    created_at: str


class MemberAdd(BaseModel):
    user_id: str
    role: str = "member"


class MemberResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: str
    status: str
    joined_at: str


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    org_id: str
    owner_id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    workspace_id: Optional[str] = None


class TeamResponse(BaseModel):
    id: str
    org_id: str
    workspace_id: Optional[str]
    owner_id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str


class InvitationCreate(BaseModel):
    email: str
    role: str = "member"
    workspace_id: Optional[str] = None
    team_id: Optional[str] = None
    expires_in_hours: int = 72


class InvitationResponse(BaseModel):
    id: str
    email: str
    role: str
    token: str
    status: str
    expires_at: str
    created_at: str


class SupportTicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "medium"
    category: Optional[str] = None


class SupportTicketResponse(BaseModel):
    id: str
    ticket_number: str
    subject: str
    description: str
    priority: str
    status: str
    category: Optional[str]
    created_at: str


class TicketMessageCreate(BaseModel):
    message: str
    message_type: str = "reply"


class WhiteLabelConfigUpdate(BaseModel):
    brand_name: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    custom_css: Optional[str] = None
    email_from_name: Optional[str] = None
    email_from_address: Optional[str] = None
    support_email: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    terms_of_service_url: Optional[str] = None
    hide_powered_by: Optional[bool] = None


class CustomDomainCreate(BaseModel):
    domain: str


class RetentionPolicyCreate(BaseModel):
    policy_name: str
    data_type: str
    retention_days: int
    auto_delete: bool = False
    archive_before_delete: bool = False


class ComplianceReportCreate(BaseModel):
    report_type: str
    framework: str
    period_start: str
    period_end: str


class SecurityCertificationCreate(BaseModel):
    certification_name: str
    certification_body: str
    issued_at: str
    expires_at: Optional[str] = None
    certificate_url: Optional[str] = None
    scope: Optional[str] = None


def _get_user_id(authorization: Optional[str] = None):
    from .auth import get_user_id_from_token_with_roles
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return get_user_id_from_token_with_roles(authorization)


def _get_user_org(user_id: str) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM organizations WHERE owner_id = ? LIMIT 1", (user_id,)).fetchone()
        return row["id"] if row else None


@router.post("/organizations", response_model=OrganizationResponse)
def create_organization(payload: OrganizationCreate, authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    org_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    slug = payload.slug or payload.name.lower().replace(" ", "-")[:30]
    with get_db() as conn:
        conn.execute(
            "INSERT INTO organizations (id, name, slug, owner_id, plan, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (org_id, payload.name, slug, user_id, payload.plan, "active", now, now),
        )
        conn.execute(
            "INSERT INTO organization_members (id, org_id, user_id, role, status, joined_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), org_id, user_id, "owner", "active", now),
        )
        conn.commit()
    log_action(user_id, "create_organization", f"org:{org_id}", {"name": payload.name, "plan": payload.plan})
    return OrganizationResponse(id=org_id, name=payload.name, slug=slug, owner_id=user_id, plan=payload.plan, tenant_id=None, status="active", created_at=now)


@router.get("/organizations", response_model=List[OrganizationResponse])
def list_organizations(authorization: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    with get_db() as conn:
        rows = conn.execute(
            "SELECT o.id, o.name, o.slug, o.owner_id, o.plan, o.tenant_id, o.status, o.created_at, om.role FROM organizations o JOIN organization_members om ON o.id = om.org_id WHERE om.user_id = ? ORDER BY o.created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        ).fetchall()
        return [OrganizationResponse(id=r["id"], name=r["name"], slug=r["slug"], owner_id=r["owner_id"], plan=r["plan"], tenant_id=r["tenant_id"], status=r["status"], created_at=r["created_at"]) for r in rows]


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
def get_organization(org_id: str, authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    with get_db() as conn:
        row = conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found")
        member = conn.execute("SELECT role FROM organization_members WHERE org_id = ? AND user_id = ?", (org_id, user_id)).fetchone()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
    return OrganizationResponse(id=row["id"], name=row["name"], slug=row["slug"], owner_id=row["owner_id"], plan=row["plan"], tenant_id=row["tenant_id"], status=row["status"], created_at=row["created_at"])


@router.post("/organizations/{org_id}/members", response_model=MemberResponse)
def add_organization_member(org_id: str, payload: MemberAdd, authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    from .organizations import add_member, get_user_org_role
    role = get_user_org_role(user_id, org_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    member = add_member(org_id, payload.user_id, payload.role)
    log_action(user_id, "add_organization_member", f"org:{org_id}", {"member_id": member["id"], "role": payload.role})
    return MemberResponse(**member, status="active", joined_at=member.get("joined_at", datetime.now(timezone.utc).isoformat()))


@router.get("/organizations/{org_id}/members", response_model=List[MemberResponse])
def list_organization_members(org_id: str, authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    from .organizations import get_user_org_role, get_org_members
    role = get_user_org_role(user_id, org_id)
    if not role:
        raise HTTPException(status_code=403, detail="Not a member")
    members = get_org_members(org_id)
    return [MemberResponse(**m, status="active") for m in members]


@router.delete("/organizations/{org_id}/members/{user_id}")
def remove_organization_member(org_id: str, user_id: str, authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    requester_id = info["user_id"]
    from .organizations import get_user_org_role, remove_member
    role = get_user_org_role(requester_id, org_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    success = remove_member(org_id, user_id)
    if success:
        log_action(requester_id, "remove_organization_member", f"org:{org_id}", {"removed_user_id": user_id})
    return {"ok": success}


@router.post("/workspaces", response_model=WorkspaceResponse)
def create_workspace(payload: WorkspaceCreate, org_id: str = Query(...), authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    from .workspaces import create_workspace as _create_workspace
    ws = _create_workspace(payload.name, org_id, user_id)
    ws["description"] = payload.description
    return WorkspaceResponse(**ws, description=payload.description)


@router.get("/workspaces", response_model=List[WorkspaceResponse])
def list_workspaces(authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    from .workspaces import get_user_workspaces
    workspaces = get_user_workspaces(user_id)
    return [WorkspaceResponse(**w) for w in workspaces]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: str, authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    from .workspaces import get_workspace as _get_workspace
    ws = _get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse(**ws)


@router.post("/teams", response_model=TeamResponse)
def create_team(payload: TeamCreate, org_id: str = Query(...), authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    from .teams import create_team as _create_team
    team_id = _create_team(user_id, payload.name)
    with get_db() as conn:
        conn.execute("UPDATE teams SET org_id = ?, workspace_id = ?, description = ? WHERE id = ?", (org_id, payload.workspace_id, payload.description, team_id))
        conn.commit()
    row = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
    return TeamResponse(**dict(row))


@router.get("/teams", response_model=List[TeamResponse])
def list_teams(authorization: Optional[str] = None, org_id: Optional[str] = Query(None)):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    with get_db() as conn:
        if org_id:
            rows = conn.execute("SELECT t.*, tm.role FROM teams t JOIN team_members tm ON t.id = tm.team_id WHERE tm.user_id = ? AND t.org_id = ?", (user_id, org_id)).fetchall()
        else:
            rows = conn.execute("SELECT t.*, tm.role FROM teams t JOIN team_members tm ON t.id = tm.team_id WHERE tm.user_id = ?", (user_id,)).fetchall()
        return [TeamResponse(**dict(r)) for r in rows]


@router.post("/invitations", response_model=InvitationResponse)
def create_invitation(payload: InvitationCreate, org_id: str = Query(...), authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    from .organizations import get_user_org_role
    role = get_user_org_role(user_id, org_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    invite_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(hours=payload.expires_in_hours)).isoformat()
    token = secrets.token_urlsafe(32)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO invitations (id, workspace_id, team_id, org_id, email, role, token, status, invited_by, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (invite_id, payload.workspace_id, payload.team_id, org_id, payload.email, payload.role, token, "pending", user_id, expires_at, now.isoformat()),
        )
        conn.commit()
    log_action(user_id, "create_invitation", f"org:{org_id}", {"email": payload.email, "role": payload.role})
    return InvitationResponse(id=invite_id, email=payload.email, role=payload.role, token=token, status="pending", expires_at=expires_at, created_at=now.isoformat())


@router.get("/invitations", response_model=List[InvitationResponse])
def list_invitations(authorization: Optional[str] = None, org_id: Optional[str] = Query(None)):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    with get_db() as conn:
        if org_id:
            rows = conn.execute("SELECT * FROM invitations WHERE org_id = ? AND email = (SELECT email FROM users WHERE id = ?)", (org_id, user_id)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM invitations WHERE email = (SELECT email FROM users WHERE id = ?)", (user_id,)).fetchall()
        return [dict(r) for r in rows]


@router.post("/invitations/{token}/accept")
def accept_invitation(token: str, authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invitations WHERE token = ? AND status = 'pending'", (token,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invitation not found or expired")
        now = datetime.now(timezone.utc).isoformat()
        if row["workspace_id"]:
            from .workspaces import accept_invitation as _accept_invitation
            _accept_invitation(token, user_id)
        elif row["team_id"]:
            from .teams import add_member
            add_member(row["team_id"], user_id, row["role"])
        conn.execute("UPDATE invitations SET status = 'accepted', accepted_at = ? WHERE id = ?", (now, row["id"]))
        conn.execute(
            "INSERT INTO organization_members (id, org_id, user_id, role, status, joined_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), row["org_id"], user_id, row["role"], "active", now),
        )
        conn.commit()
    log_action(user_id, "accept_invitation", f"org:{row['org_id']}", {"invitation_id": row["id"]})
    return {"ok": True}


@router.get("/audit-logs")
def list_audit_logs(authorization: Optional[str] = None, org_id: Optional[str] = Query(None), action: Optional[str] = Query(None), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    with get_db() as conn:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        if org_id:
            query += " AND org_id = ?"
            params.append(org_id)
        if action:
            query += " AND action = ?"
            params.append(action)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.post("/audit-logs")
def create_audit_log(action: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None, details: Optional[str] = None, authorization: Optional[str] = None):
    info = _get_user_id(authorization)
    user_id = info["user_id"]
    log_id = log_action(user_id, action, f"{resource_type}:{resource_id}" if resource_type and resource_id else None, {"details": details})
    return log_id
