"""Tests for enterprise collaboration platform."""

import pytest
from unittest.mock import patch

from app.enterprise.service import OrganizationService, org_service
from app.enterprise.rbac import rbac
from app.enterprise.models import ORG_ROLES, WORKSPACE_ROLES


class TestOrganizationService:
    def setup_method(self):
        """Reset service before each test."""
        org_service._orgs.clear()
        org_service._workspaces.clear()
        org_service._org_members.clear()
        org_service._workspace_members.clear()

    def test_create_organization(self):
        org, membership = org_service.create_organization("Acme Corp", "user-1")
        assert org.name == "Acme Corp"
        assert org.owner_id == "user-1"
        assert org.slug == "acme-corp"
        assert membership.role == "owner"
        assert membership.user_id == "user-1"

    def test_get_organization(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        found = org_service.get_organization(org.id)
        assert found is not None
        assert found.name == "Test Org"

    def test_get_user_organizations(self):
        org_service.create_organization("Org 1", "user-1")
        org_service.create_organization("Org 2", "user-1")
        orgs = org_service.get_user_organizations("user-1")
        assert len(orgs) == 2

    def test_update_organization(self):
        org, _ = org_service.create_organization("Old Name", "user-1")
        updated = org_service.update_organization(org.id, name="New Name")
        assert updated.name == "New Name"
        assert updated.slug == "new-name"

    def test_delete_organization(self):
        org, _ = org_service.create_organization("To Delete", "user-1")
        assert org_service.delete_organization(org.id) is True
        assert org_service.get_organization(org.id) is None


class TestOrganizationMembers:
    def setup_method(self):
        org_service._orgs.clear()
        org_service._workspaces.clear()
        org_service._org_members.clear()
        org_service._workspace_members.clear()

    def test_add_member(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        membership = org_service.add_member(org.id, "user-2", "member", "user-1")
        assert membership is not None
        assert membership.role == "member"
        assert membership.status == "invited"

    def test_add_member_invalid_role(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        membership = org_service.add_member(org.id, "user-2", "superadmin")
        assert membership is None

    def test_get_membership(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        org_service.add_member(org.id, "user-2", "member")
        membership = org_service.get_membership(org.id, "user-2")
        assert membership is not None
        assert membership.role == "member"

    def test_update_member_role(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        org_service.add_member(org.id, "user-2", "member")
        updated = org_service.update_member_role(org.id, "user-2", "admin")
        assert updated is not None
        assert updated.role == "admin"

    def test_remove_member(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        org_service.add_member(org.id, "user-2", "member")
        assert org_service.remove_member(org.id, "user-2") is True
        membership = org_service.get_membership(org.id, "user-2")
        assert membership.status == "removed"

    def test_list_members(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        org_service.add_member(org.id, "user-2", "member")
        org_service.add_member(org.id, "user-3", "member")
        members = org_service.list_members(org.id)
        assert len(members) == 3  # owner + 2 members


class TestWorkspaces:
    def setup_method(self):
        org_service._orgs.clear()
        org_service._workspaces.clear()
        org_service._org_members.clear()
        org_service._workspace_members.clear()

    def test_create_workspace(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        ws, membership = org_service.create_workspace(org.id, "Engineering", "user-1")
        assert ws.name == "Engineering"
        assert ws.organization_id == org.id
        assert membership.role == "owner"

    def test_get_organization_workspaces(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        org_service.create_workspace(org.id, "Team A", "user-1")
        org_service.create_workspace(org.id, "Team B", "user-1")
        workspaces = org_service.get_organization_workspaces(org.id)
        assert len(workspaces) == 2

    def test_archive_workspace(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        ws, _ = org_service.create_workspace(org.id, "To Archive", "user-1")
        assert org_service.archive_workspace(ws.id) is True
        archived = org_service.get_workspace(ws.id)
        assert archived.is_archived is True
        assert archived.is_active is False


class TestRBAC:
    def setup_method(self):
        org_service._orgs.clear()
        org_service._workspaces.clear()
        org_service._org_members.clear()
        org_service._workspace_members.clear()

    def test_owner_has_all_permissions(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        assert rbac.has_org_permission("user-1", org.id, "org:read") is True
        assert rbac.has_org_permission("user-1", org.id, "org:write") is True
        assert rbac.has_org_permission("user-1", org.id, "org:delete") is True
        assert rbac.has_org_permission("user-1", org.id, "member:invite") is True

    def test_member_limited_permissions(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        org_service.add_member(org.id, "user-2", "member")
        assert rbac.has_org_permission("user-2", org.id, "org:read") is True
        assert rbac.has_org_permission("user-2", org.id, "org:write") is False
        assert rbac.has_org_permission("user-2", org.id, "member:invite") is False

    def test_guest_minimal_permissions(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        org_service.add_member(org.id, "user-2", "guest")
        assert rbac.has_org_permission("user-2", org.id, "org:read") is True
        assert rbac.has_org_permission("user-2", org.id, "workspace:write") is False

    def test_workspace_permissions(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        ws, _ = org_service.create_workspace(org.id, "Test WS", "user-1")
        assert rbac.has_workspace_permission("user-1", ws.id, "workspace:delete") is True
        assert rbac.has_workspace_permission("user-1", ws.id, "document:create") is True

    def test_can_manage_member(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        org_service.add_member(org.id, "user-2", "member")
        # Owner can manage member
        assert rbac.can_manage_member("user-1", "user-2", org.id) is True
        # Member cannot manage owner
        assert rbac.can_manage_member("user-2", "user-1", org.id) is False

    def test_require_org_role(self):
        org, _ = org_service.create_organization("Test Org", "user-1")
        org_service.add_member(org.id, "user-2", "manager")
        assert rbac.require_org_role("user-2", org.id, "member") is True
        assert rbac.require_org_role("user-2", org.id, "admin") is False


class TestRoles:
    def test_org_roles_defined(self):
        assert "owner" in ORG_ROLES
        assert "admin" in ORG_ROLES
        assert "member" in ORG_ROLES
        assert "guest" in ORG_ROLES

    def test_workspace_roles_defined(self):
        assert "owner" in WORKSPACE_ROLES
        assert "admin" in WORKSPACE_ROLES
        assert "editor" in WORKSPACE_ROLES
        assert "viewer" in WORKSPACE_ROLES

    def test_owner_has_most_permissions(self):
        owner_perms = set(ORG_ROLES["owner"]["permissions"])
        admin_perms = set(ORG_ROLES["admin"]["permissions"])
        assert owner_perms > admin_perms  # Owner has strictly more permissions
