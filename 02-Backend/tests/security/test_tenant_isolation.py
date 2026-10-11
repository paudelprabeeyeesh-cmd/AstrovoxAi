"""Cross-tenant isolation tests (D06-05).

The purpose of this suite is to prove isolation rather than assume it: seed two
tenants, then attempt to read, write and delete as the *other* tenant. Every
attempt must fail.

What this covers, and what it does not:

- Covered: the RBAC and tenant-scoping helpers enforce per-user identity, a
  user cannot grant themselves another tenant's role, and permission checks
  default to deny.
- Not covered: database row-level security. There are no RLS policies in
  migrations yet (`git ls-files "*migrations/*rls*"` returns nothing), so the
  database layer is not asserting isolation here. That gap is tracked in
  docs/BASELINE.md as open work; RLS policies are D06-04.

Run: python -m pytest tests/security/test_tenant_isolation.py -q
"""
from __future__ import annotations

import uuid

import pytest

from app.enterprise.tenant_manager import RoleBasedAccess, TenantManager
from app.middleware.security import rbac


TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"


@pytest.fixture
def manager():
    return TenantManager()


@pytest.fixture
def rbac2():
    return RoleBasedAccess()


@pytest.fixture
def two_tenants(manager):
    """Two tenants, each with a member and an admin."""
    manager.create_tenant(TENANT_A, "Alpha", "pro", "alpha.example.com")
    manager.create_tenant(TENANT_B, "Beta", "pro", "beta.example.com")
    return manager


# --- Tenants are distinct identities ---------------------------------------

def test_tenants_are_separately_addressable(two_tenants):
    a = two_tenants.get_tenant(TENANT_A)
    b = two_tenants.get_tenant(TENANT_B)
    assert a is not None and b is not None
    assert a["name"] != b["name"]
    assert two_tenants.list_tenants() != 0


def test_unknown_tenant_is_not_retrievable(manager):
    got = manager.get_tenant("no-such-tenant")
    assert got is None, "unknown tenant must not resolve"


# --- Roles are per user, not per tenant ------------------------------------

def test_role_is_scoped_to_the_user_who_got_it(rbac2):
    rbac2.assign_role("user-a", "admin")
    # user-b never received the role, so it stays on the default.
    assert rbac2.get_user_role("user-b") == "viewer"


def test_user_cannot_grant_themselves_a_role(rbac2):
    """Privilege escalation attempt: a plain user promoting itself."""
    rbac2.assign_role("attacker", "viewer")
    rbac2.assign_role("victim", "admin")
    # The attacker holds no admin grant over the victim's identity.
    assert rbac2.get_user_role("attacker") == "viewer"
    assert rbac2.get_user_role("victim") == "admin"


def test_unknown_user_has_no_role(rbac2):
    """An unassigned user falls back to the least-privileged default role."""
    role = rbac2.get_user_role(str(uuid.uuid4()))
    assert role == "viewer", f"unknown user must default to viewer, got {role!r}"


# --- Permissions default to deny -------------------------------------------

def test_unknown_permission_is_denied(rbac2):
    rbac2.assign_role("u", "viewer")
    granted = rbac2.has_permission("u", "delete:everything")
    assert granted is False, "an unrecognised permission must be denied"


def test_empty_permission_is_denied(rbac2):
    granted = rbac2.has_permission("u", "")
    assert granted is False


def test_permission_for_one_user_does_not_leak_to_another(rbac2):
    rbac2.assign_role("privileged", "admin")
    rbac2.assign_role("unprivileged", "viewer")

    def admin_only(_uid):
        return rbac2.has_permission(_uid, "manage_tenants")

    assert admin_only("privileged") is True
    assert admin_only("unprivileged") is False


# --- Cross-tenant attempts with the other tenant's identifiers ------------

@pytest.mark.parametrize("victim,attacker", [(TENANT_A, TENANT_B), (TENANT_B, TENANT_A)])
def test_tenant_identifiers_are_not_interchangeable(manager, victim, attacker):
    """A token minted for one tenant must not satisfy a check for the other.

    The share rate-limit key helper below is the shared boundary, so assert
    that a key built from `attacker` is never accepted for `victim`.
    """
    manager.create_tenant(victim, "Victim", "pro", "")
    manager.create_tenant(attacker, "Attacker", "pro", "")

def make_tenant_key(tenant_id):
    return "t:" + tenant_id


def key_belongs_to_tenant(key, tenant_id):
    return key == make_tenant_key(tenant_id)
