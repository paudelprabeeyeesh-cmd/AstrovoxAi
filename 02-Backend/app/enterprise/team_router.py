"""Organization and team management APIs."""

from fastapi import APIRouter, HTTPException, status, Header, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.utils.auth.auth_utils import get_user_id_from_token
from ..enterprise.service import org_service
from ..enterprise.rbac import rbac
from ..enterprise.abac import abac

router = APIRouter(prefix="/api/enterprise/teams", tags=["enterprise-teams"])


class TeamCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    team_type: Optional[str] = "team"
    member_ids: Optional[List[str]] = []


class TeamUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


@router.post("/workspaces/{workspace_id}/teams")
async def create_team_in_workspace(workspace_id: str, request: TeamCreateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, workspace_id, "member:invite"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    ws = org_service.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    team, _ = org_service.create_workspace(
        organization_id=ws.organization_id,
        name=request.name,
        owner_id=user_id,
        description=request.description or "",
        ws_type=request.team_type or "team",
    )
    for member_id in request.member_ids or []:
        org_service.add_workspace_member(team.id, member_id, "member")
    return {
        "status": "OK",
        "team": {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "type": team.type,
            "organization_id": team.organization_id,
            "member_count": team.member_count,
        },
    }


@router.get("/workspaces/{workspace_id}/teams")
async def list_teams_in_workspace(workspace_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, workspace_id, "workspace:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    ws = org_service.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    teams = org_service.get_organization_workspaces(ws.organization_id)
    return {
        "status": "OK",
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "type": t.type,
                "member_count": t.member_count,
            }
            for t in teams
        ],
    }


@router.get("/workspaces/{workspace_id}/teams/{team_id}")
async def get_team(workspace_id: str, team_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, workspace_id, "workspace:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    team = org_service.get_workspace(team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    members = org_service.list_workspace_members(team_id)
    return {
        "status": "OK",
        "team": {
            "id": team.id,
            "name": team.name,
            "slug": team.slug,
            "description": team.description,
            "type": team.type,
            "member_count": team.member_count,
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
        },
    }


@router.patch("/workspaces/{workspace_id}/teams/{team_id}")
async def update_team(workspace_id: str, team_id: str, request: TeamUpdateRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, workspace_id, "workspace:write"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    team = org_service.update_workspace(team_id, name=request.name, description=request.description)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return {"status": "OK", "team": {"id": team.id, "name": team.name}}


@router.delete("/workspaces/{workspace_id}/teams/{team_id}")
async def delete_team(workspace_id: str, team_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, workspace_id, "workspace:delete"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    ws = org_service.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if ws.organization_id != org_service.get_workspace(team_id).organization_id if org_service.get_workspace(team_id) else False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team does not belong to this workspace")
    org_service.archive_workspace(team_id)
    return {"status": "OK", "message": "Team deleted"}


@router.post("/workspaces/{workspace_id}/teams/{team_id}/members")
async def add_team_member(workspace_id: str, team_id: str, request: dict, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    member_user_id = request.get("user_id")
    role = request.get("role", "member")
    if not rbac.has_workspace_permission(user_id, workspace_id, "member:invite"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    membership = org_service.add_workspace_member(team_id, member_user_id, role)
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


@router.delete("/workspaces/{workspace_id}/teams/{team_id}/members/{member_user_id}")
async def remove_team_member(workspace_id: str, team_id: str, member_user_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    if not rbac.has_workspace_permission(user_id, workspace_id, "member:remove"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not org_service.remove_workspace_member(team_id, member_user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return {"status": "OK", "message": "Member removed from team"}
