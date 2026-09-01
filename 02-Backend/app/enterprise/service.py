"""Organization service — business logic for orgs, workspaces, memberships."""

import re
import time
import uuid
from typing import Optional

from .models import (
    Organization,
    Workspace,
    OrganizationMembership,
    WorkspaceMembership,
    ORG_ROLES,
    WORKSPACE_ROLES,
)


def _slugify(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug[:64] or "org"


class OrganizationService:
    """Service for organization and workspace management."""

    def __init__(self):
        self._orgs: dict[str, Organization] = {}
        self._workspaces: dict[str, Workspace] = {}
        self._org_members: dict[str, OrganizationMembership] = {}
        self._workspace_members: dict[str, WorkspaceMembership] = {}

    # ========================================================================
    # Organizations
    # ========================================================================

    def create_organization(
        self,
        name: str,
        owner_id: str,
        description: str = "",
        website: str = "",
    ) -> tuple[Organization, OrganizationMembership]:
        """Create a new organization with owner membership."""
        org_id = str(uuid.uuid4())
        slug = _slugify(name)

        org = Organization(
            id=org_id,
            name=name,
            slug=slug,
            description=description,
            website=website,
            owner_id=owner_id,
        )
        self._orgs[org_id] = org

        # Add owner membership
        membership = OrganizationMembership(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            user_id=owner_id,
            role="owner",
        )
        self._org_members[membership.id] = membership
        org.member_count = 1

        return org, membership

    def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID."""
        return self._orgs.get(org_id)

    def get_user_organizations(self, user_id: str) -> list[Organization]:
        """Get all organizations a user belongs to."""
        org_ids = [
            m.organization_id
            for m in self._org_members.values()
            if m.user_id == user_id and m.status == "active"
        ]
        return [self._orgs[oid] for oid in org_ids if oid in self._orgs]

    def update_organization(
        self,
        org_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        website: Optional[str] = None,
    ) -> Optional[Organization]:
        """Update organization details."""
        org = self._orgs.get(org_id)
        if not org:
            return None
        if name:
            org.name = name
            org.slug = _slugify(name)
        if description is not None:
            org.description = description
        if website is not None:
            org.website = website
        org.updated_at = time.time()
        return org

    def delete_organization(self, org_id: str) -> bool:
        """Delete an organization and all its workspaces."""
        if org_id not in self._orgs:
            return False
        # Remove workspaces
        for ws in list(self._workspaces.values()):
            if ws.organization_id == org_id:
                del self._workspaces[ws.id]
        # Remove memberships
        for m in list(self._org_members.values()):
            if m.organization_id == org_id:
                del self._org_members[m.id]
        del self._orgs[org_id]
        return True

    # ========================================================================
    # Organization Members
    # ========================================================================

    def add_member(
        self,
        organization_id: str,
        user_id: str,
        role: str = "member",
        invited_by: str = "",
    ) -> Optional[OrganizationMembership]:
        """Add a member to an organization."""
        if organization_id not in self._orgs:
            return None
        if role not in ORG_ROLES:
            return None

        membership = OrganizationMembership(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            status="invited",
            invited_by=invited_by,
        )
        self._org_members[membership.id] = membership
        self._orgs[organization_id].member_count += 1
        return membership

    def get_membership(self, organization_id: str, user_id: str) -> Optional[OrganizationMembership]:
        """Get a user's membership in an organization."""
        for m in self._org_members.values():
            if m.organization_id == organization_id and m.user_id == user_id:
                return m
        return None

    def update_member_role(
        self,
        organization_id: str,
        user_id: str,
        role: str,
    ) -> Optional[OrganizationMembership]:
        """Update a member's role."""
        membership = self.get_membership(organization_id, user_id)
        if not membership or role not in ORG_ROLES:
            return None
        membership.role = role
        membership.updated_at = time.time()
        return membership

    def remove_member(self, organization_id: str, user_id: str) -> bool:
        """Remove a member from an organization."""
        membership = self.get_membership(organization_id, user_id)
        if not membership:
            return False
        membership.status = "removed"
        membership.updated_at = time.time()
        if organization_id in self._orgs:
            self._orgs[organization_id].member_count = max(0, self._orgs[organization_id].member_count - 1)
        return True

    def list_members(self, organization_id: str) -> list[OrganizationMembership]:
        """List all members of an organization."""
        return [
            m for m in self._org_members.values()
            if m.organization_id == organization_id and m.status != "removed"
        ]

    # ========================================================================
    # Workspaces
    # ========================================================================

    def create_workspace(
        self,
        organization_id: str,
        name: str,
        owner_id: str,
        description: str = "",
        ws_type: str = "team",
    ) -> tuple[Workspace, WorkspaceMembership]:
        """Create a new workspace within an organization."""
        ws_id = str(uuid.uuid4())

        ws = Workspace(
            id=ws_id,
            organization_id=organization_id,
            name=name,
            slug=_slugify(name),
            description=description,
            type=ws_type,
            owner_id=owner_id,
        )
        self._workspaces[ws_id] = ws

        # Add owner membership
        membership = WorkspaceMembership(
            id=str(uuid.uuid4()),
            workspace_id=ws_id,
            user_id=owner_id,
            role="owner",
        )
        self._workspace_members[membership.id] = membership
        ws.member_count = 1

        # Update org workspace count
        if organization_id in self._orgs:
            self._orgs[organization_id].workspace_count += 1

        return ws, membership

    def get_workspace(self, ws_id: str) -> Optional[Workspace]:
        """Get workspace by ID."""
        return self._workspaces.get(ws_id)

    def get_organization_workspaces(self, organization_id: str) -> list[Workspace]:
        """List all workspaces in an organization."""
        return [
            ws for ws in self._workspaces.values()
            if ws.organization_id == organization_id and ws.is_active
        ]

    def get_user_workspaces(self, user_id: str, organization_id: str) -> list[Workspace]:
        """Get workspaces a user has access to in an organization."""
        ws_ids = [
            m.workspace_id
            for m in self._workspace_members.values()
            if m.user_id == user_id and m.status == "active"
        ]
        return [
            self._workspaces[wid]
            for wid in ws_ids
            if wid in self._workspaces
            and self._workspaces[wid].organization_id == organization_id
        ]

    def update_workspace(
        self,
        ws_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Workspace]:
        """Update workspace details."""
        ws = self._workspaces.get(ws_id)
        if not ws:
            return None
        if name:
            ws.name = name
            ws.slug = _slugify(name)
        if description is not None:
            ws.description = description
        ws.updated_at = time.time()
        return ws

    def archive_workspace(self, ws_id: str) -> bool:
        """Archive a workspace."""
        ws = self._workspaces.get(ws_id)
        if not ws:
            return False
        ws.is_archived = True
        ws.is_active = False
        ws.updated_at = time.time()
        return True

    # ========================================================================
    # Workspace Members
    # ========================================================================

    def add_workspace_member(
        self,
        workspace_id: str,
        user_id: str,
        role: str = "viewer",
    ) -> Optional[WorkspaceMembership]:
        """Add a member to a workspace."""
        if workspace_id not in self._workspaces:
            return None
        if role not in WORKSPACE_ROLES:
            return None

        membership = WorkspaceMembership(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self._workspace_members[membership.id] = membership
        self._workspaces[workspace_id].member_count += 1
        return membership

    def get_workspace_membership(self, workspace_id: str, user_id: str) -> Optional[WorkspaceMembership]:
        """Get a user's workspace membership."""
        for m in self._workspace_members.values():
            if m.workspace_id == workspace_id and m.user_id == user_id:
                return m
        return None

    def update_workspace_member_role(self, workspace_id: str, user_id: str, role: str) -> Optional[WorkspaceMembership]:
        """Update a workspace member's role."""
        membership = self.get_workspace_membership(workspace_id, user_id)
        if not membership or role not in WORKSPACE_ROLES:
            return None
        membership.role = role
        membership.updated_at = time.time()
        return membership

    def remove_workspace_member(self, workspace_id: str, user_id: str) -> bool:
        """Remove a member from a workspace."""
        membership = self.get_workspace_membership(workspace_id, user_id)
        if not membership:
            return False
        membership.status = "removed"
        membership.updated_at = time.time()
        if workspace_id in self._workspaces:
            self._workspaces[workspace_id].member_count = max(0, self._workspaces[workspace_id].member_count - 1)
        return True

    def list_workspace_members(self, workspace_id: str) -> list[WorkspaceMembership]:
        """List all members of a workspace."""
        return [
            m for m in self._workspace_members.values()
            if m.workspace_id == workspace_id and m.status != "removed"
        ]


# Global service instance
org_service = OrganizationService()
