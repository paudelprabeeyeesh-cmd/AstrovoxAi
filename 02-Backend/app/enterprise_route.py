"""Enterprise API routes — organizations, teams, admin."""

from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field
from typing import Optional

from .enterprise import org_manager, OrganizationRole
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class InviteRequest(BaseModel):
    email: str
    role: str = "member"


class RoleUpdateRequest(BaseModel):
    user_id: str
    role: str


@router.post("/organizations")
async def create_organization(request: CreateOrgRequest, authorization: str = Header(None)):
    """Create a new organization."""
    user_id = get_user_id_from_token(authorization)
    org = org_manager.create_organization(request.name, user_id)
    return {
        "status": "OK",
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "created_at": org.created_at,
        },
    }


@router.get("/organizations")
async def list_organizations(authorization: str = Header(None)):
    """List user's organizations."""
    user_id = get_user_id_from_token(authorization)
    orgs = org_manager.get_user_organizations(user_id)
    return {
        "status": "OK",
        "organizations": [
            {"id": o.id, "name": o.name, "slug": o.slug, "plan": o.plan}
            for o in orgs
        ],
    }


@router.get("/organizations/{org_id}")
async def get_organization(org_id: str, authorization: str = Header(None)):
    """Get organization details."""
    user_id = get_user_id_from_token(authorization)
    org = org_manager.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    stats = org_manager.get_org_stats(org_id)
    return {"status": "OK", "organization": {"id": org.id, "name": org.name, "stats": stats}}


@router.post("/organizations/{org_id}/invite")
async def invite_member(
    org_id: str, request: InviteRequest, authorization: str = Header(None)
):
    """Invite a member to the organization."""
    user_id = get_user_id_from_token(authorization)

    try:
        role = OrganizationRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    invitation = org_manager.invite_member(org_id, request.email, role, user_id)
    if not invitation:
        raise HTTPException(status_code=400, detail="Failed to create invitation")

    return {
        "status": "OK",
        "invitation": {
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role.value,
            "status": invitation.status.value,
        },
    }


@router.get("/organizations/{org_id}/members")
async def list_members(org_id: str, authorization: str = Header(None)):
    """List organization members."""
    user_id = get_user_id_from_token(authorization)
    members = org_manager.get_members(org_id)

    return {
        "status": "OK",
        "members": [
            {
                "user_id": m.user_id,
                "role": m.role.value,
                "joined_at": m.joined_at,
            }
            for m in members
        ],
    }


@router.get("/organizations/{org_id}/audit-log")
async def get_audit_log(
    org_id: str,
    authorization: str = Header(None),
    limit: int = 100,
):
    """Get organization audit log."""
    user_id = get_user_id_from_token(authorization)
    entries = org_manager.get_audit_log(org_id, limit=limit)

    return {
        "status": "OK",
        "entries": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "action": e.action,
                "resource_type": e.resource_type,
                "timestamp": e.timestamp,
                "details": e.details,
            }
            for e in entries
        ],
    }
