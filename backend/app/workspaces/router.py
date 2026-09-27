"""Workspace API router."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from .models import WorkspaceCreate, WorkspaceResponse, WorkspaceMember, InviteRequest, WorkspaceInvitation
from .service import WorkspaceService

logger = logging.getLogger(__name__)
workspace_service = WorkspaceService()
router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class MessageResponse(BaseModel):
    message: str


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(body: WorkspaceCreate, user_id: str = Depends(lambda: "user-1")):
    return workspace_service.create_workspace(name=body.name, owner_id=user_id, description=body.description)


@router.get("/", response_model=list[WorkspaceResponse])
async def list_workspaces(user_id: str = Depends(lambda: "user-1")):
    return workspace_service.list_user_workspaces(user_id)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str, user_id: str = Depends(lambda: "user-1")):
    workspace = workspace_service.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(workspace_id: str, body: WorkspaceCreate, user_id: str = Depends(lambda: "user-1")):
    workspace = workspace_service.update_workspace(workspace_id, name=body.name, description=body.description)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


@router.delete("/{workspace_id}", response_model=MessageResponse)
async def delete_workspace(workspace_id: str, user_id: str = Depends(lambda: "user-1")):
    if not workspace_service.delete_workspace(workspace_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return MessageResponse(message="Workspace deleted successfully")


@router.post("/{workspace_id}/invitations", response_model=WorkspaceInvitation, status_code=status.HTTP_201_CREATED)
async def invite_member(workspace_id: str, body: InviteRequest, user_id: str = Depends(lambda: "user-1")):
    invitation = workspace_service.invite_member(workspace_id, body.email, body.role, user_id)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return invitation


@router.post("/invitations/accept", response_model=WorkspaceMember)
async def accept_invitation(token: str, user_id: str = Depends(lambda: "user-1")):
    member = workspace_service.accept_invitation(token, user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invitation token")
    return member


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMember])
async def get_members(workspace_id: str, user_id: str = Depends(lambda: "user-1")):
    return workspace_service.get_members(workspace_id)


@router.delete("/{workspace_id}/members/{member_id}", response_model=MessageResponse)
async def remove_member(workspace_id: str, member_id: str, user_id: str = Depends(lambda: "user-1")):
    if not workspace_service.remove_member(workspace_id, member_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return MessageResponse(message="Member removed successfully")
