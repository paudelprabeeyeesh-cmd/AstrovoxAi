"""Pydantic models for workspaces."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class WorkspaceResponse(WorkspaceBase):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    member_count: int = 0


class WorkspaceMember(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: str
    email: Optional[str] = None
    joined_at: datetime


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(owner|admin|member|viewer)$")


class WorkspaceInvitation(BaseModel):
    id: str
    workspace_id: str
    email: str
    role: str
    token: str
    created_at: datetime
    expires_at: Optional[datetime] = None
