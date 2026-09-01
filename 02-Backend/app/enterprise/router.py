"""Enterprise API endpoints — organizations, workspaces, memberships."""

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from ..auth_utils import get_user_id_from_token
from .service import org_service
from .rbac import rbac
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


# ============================================================================
# Organizations
# ============================================================================

@router.post("/organizations")
async def create_organization(request: CreateOrgRequest, authorization: str = Header(None)):
    """Create a new organization."""
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
    """List user's organizations."""
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
    """Get organization details."""
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
    """Update organization details."""
    user_id = get_user_id_from_token(authorization)

    if not rbac.has_org_permission(user_id, org_id, "org:write"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    org = org_service.update_organization(
        org_id,
        name=request.name,
        description=request.description,
        website=request.website,
    )
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return {"status": "OK", "organization": {"id": org.id, "name": org.name, "slug": org.slug}}


@router.delete("/organizations/{org_id}")
async def delete_organization(org_id: str, authorization: str = Header(None)):
    """Delete an organization."""
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
    """Invite a member to an organization."""
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
    """List organization members."""
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
    """Update a member's role."""
    user_id = get_user_id_from_token(authorization)

    if not rbac.can_manage_member(user_id, member_user_id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot manage this member")

    membership = org_service.update_member_role(org_id, member_user_id, request.role)
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update role")

    return {"status": "OK", "role": membership.role}


@router.delete("/organizations/{org_id}/members/{member_user_id}")
async def remove_member(org_id: str, member_user_id: str, authorization: str = Header(None)):
    """Remove a member from an organization."""
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
    """Create a new workspace."""
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
    """List workspaces in an organization."""
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
    """Get workspace details."""
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
    """Update workspace details."""
    user_id = get_user_id_from_token(authorization)

    if not rbac.has_workspace_permission(user_id, ws_id, "workspace:write"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    ws = org_service.update_workspace(ws_id, name=request.name, description=request.description)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return {"status": "OK", "workspace": {"id": ws.id, "name": ws.name}}


@router.post("/workspaces/{ws_id}/archive")
async def archive_workspace(ws_id: str, authorization: str = Header(None)):
    """Archive a workspace."""
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
    """Add a member to a workspace."""
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
    """List workspace members."""
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
    """Update a workspace member's role."""
    user_id = get_user_id_from_token(authorization)

    if not rbac.has_workspace_permission(user_id, ws_id, "member:manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    membership = org_service.update_workspace_member_role(ws_id, member_user_id, request.role)
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update role")

    return {"status": "OK", "role": membership.role}


@router.delete("/workspaces/{ws_id}/members/{member_user_id}")
async def remove_workspace_member(ws_id: str, member_user_id: str, authorization: str = Header(None)):
    """Remove a member from a workspace."""
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
    """List available organization roles."""
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
    """List available workspace roles."""
    get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "roles": [
            {"name": name, "description": data["description"], "permissions": data["permissions"]}
            for name, data in WORKSPACE_ROLES.items()
        ],
    }
