"""Tests for permission_auditor module."""

import pytest

from security_audit.permission_auditor import AccessAuditResult, Permission, PermissionAuditor, Role


@pytest.fixture
def auditor():
    return PermissionAuditor()


class TestPermission:
    def test_permission_creation(self):
        perm = Permission(name="read", resource="data", actions=["get", "list"])
        assert perm.name == "read"
        assert perm.resource == "data"
        assert "get" in perm.actions

    def test_permission_default_actions(self):
        perm = Permission(name="write", resource="data")
        assert perm.actions == []


class TestRole:
    def test_role_creation(self):
        role = Role(name="admin")
        assert role.name == "admin"
        assert role.permissions == []


class TestPermissionAuditor:
    def test_create_role(self, auditor):
        role = auditor.create_role("admin")
        assert role.name == "admin"
        assert "admin" in auditor._roles

    def test_create_role_with_permissions(self, auditor):
        perm = Permission(name="read", resource="data")
        role = auditor.create_role("reader", permissions=[perm])
        assert len(role.permissions) == 1

    def test_grant_permission(self, auditor):
        perm = Permission(name="write", resource="data")
        auditor.grant("editor", perm)
        assert len(auditor.get_role_permissions("editor")) == 1

    def test_revoke_permission(self, auditor):
        perm = Permission(name="write", resource="data")
        auditor.grant("editor", perm)
        auditor.revoke("editor", perm)
        assert len(auditor.get_role_permissions("editor")) == 0

    def test_audit_access_granted(self, auditor):
        perm = Permission(name="read", resource="data")
        auditor.grant("reader", perm)
        result = auditor.audit_access("user1", "reader", "read")
        assert result.granted is True
        assert result.reason == "granted"

    def test_audit_access_denied(self, auditor):
        result = auditor.audit_access("user1", "nonexistent", "read")
        assert result.granted is False
        assert result.reason == "role_not_found"

    def test_audit_access_wrong_permission(self, auditor):
        perm = Permission(name="read", resource="data")
        auditor.grant("reader", perm)
        result = auditor.audit_access("user1", "reader", "write")
        assert result.granted is False
        assert result.reason == "permission_denied"

    def test_generate_matrix_empty(self, auditor):
        matrix = auditor.generate_matrix()
        assert matrix == {}

    def test_generate_matrix_populated(self, auditor):
        auditor.create_role("admin")
        auditor.create_role("guest")
        auditor.grant("admin", Permission(name="read", resource="data"))
        auditor.grant("admin", Permission(name="write", resource="data"))
        auditor.grant("guest", Permission(name="read", resource="data"))
        matrix = auditor.generate_matrix()
        assert "admin" in matrix
        assert "read" in matrix["admin"]
        assert "write" in matrix["admin"]

    def test_get_role_permissions_missing_role(self, auditor):
        assert auditor.get_role_permissions("missing") == []

    def test_audit_log_records_results(self, auditor):
        perm = Permission(name="read", resource="data")
        auditor.grant("reader", perm)
        auditor.audit_access("user1", "reader", "read")
        auditor.audit_access("user2", "reader", "write")
        log = auditor.get_audit_log()
        assert len(log) == 2

    def test_audit_result_fields(self, auditor):
        result = auditor.audit_access("alice", "admin", "config")
        assert result.user == "alice"
        assert result.role == "admin"
        assert result.permission == "config"

    def test_multiple_grants_same_role(self, auditor):
        auditor.grant("editor", Permission(name="read", resource="data"))
        auditor.grant("editor", Permission(name="write", resource="data"))
        auditor.grant("editor", Permission(name="delete", resource="data"))
        assert len(auditor.get_role_permissions("editor")) == 3
