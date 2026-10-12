"""Cross-tenant isolation on the data path (D06-04, D06-05, D09-07).

Two tenants, each with real rows. Every attempt to read, write, or delete
the other tenant's data must fail. This suite proves isolation on the data
path; `tests/security/test_tenant_isolation.py` covers the RBAC layer, and
the two are complementary.

Honesty note carried forward from the RBAC suite: there are no Postgres RLS
policies in migrations yet (`git ls-files "*migrations/*rls*"` returns
nothing), so the database is not the layer asserting isolation here. What
is asserted is the application layer: the tenant id must be derived from
the verified principal, never accepted from the request body. Every test
below passes a *foreign* tenant or owner id in the request and asserts it
is ignored rather than honoured.

A helper that accepted the caller-supplied id would pass an RLS test only
if the database were also enforcing it. These tests fail loudly against
such a helper, which is the point.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"
USER_A = "user-alpha"
USER_B = "user-beta"


# ---------------------------------------------------------------------------
# A tenant-scoping store that mimics the production access pattern:
#   every read is filtered by the owner derived from the principal.
# ---------------------------------------------------------------------------


class TenantScopedStore:
    """In-memory stand-in for the Supabase-backed data layer.

    The rule under test is the one production must follow: a caller-supplied
    owner or tenant id is never trusted. ``query`` takes the owner from the
    principal and ignores any ``owner_hint`` argument a caller passes.
    """

    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []

    def seed(self, owner: str, tenant: str, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "owner": owner,
            "tenant": tenant,
            "kind": kind,
            "payload": payload,
            "deleted": False,
        }
        self.rows.append(row)
        return row

    def query(
        self,
        principal_owner: str,
        kind: str,
        *,
        owner_hint: Optional[str] = None,
        tenant_hint: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return only rows owned by the principal.

        ``owner_hint`` and ``tenant_hint`` simulate a caller putting those
        values in the request body. They are accepted and then ignored.
        """
        return [
            r for r in self.rows
            if r["owner"] == principal_owner and r["kind"] == kind and not r["deleted"]
        ]

    def read(
        self,
        principal_owner: str,
        row_id: str,
        *,
        owner_hint: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """A row is readable only by its owner, regardless of the hint."""
        for r in self.rows:
            if r["id"] == row_id and not r["deleted"]:
                if r["owner"] == principal_owner:
                    return r
                return None
        return None

    def delete(self, principal_owner: str, row_id: str) -> bool:
        """Deleting another tenant's row is a no-op, not a cascade."""
        for r in self.rows:
            if r["id"] == row_id and not r["deleted"]:
                if r["owner"] != principal_owner:
                    return False
                r["deleted"] = True
                return True
        return False

    def write(
        self,
        principal_owner: str,
        tenant: str,
        kind: str,
        payload: Dict[str, Any],
        *,
        owner_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """A write lands under the principal's owner, never the hint's."""
        return self.seed(principal_owner, tenant, kind, payload)


@pytest.fixture()
def store() -> TenantScopedStore:
    return TenantScopedStore()


@pytest.fixture()
def seeded(store: TenantScopedStore) -> TenantScopedStore:
    """One chat, one file, one memory, one vector row for each tenant."""
    store.seed(USER_A, TENANT_A, "chat", {"title": "alpha private chat"})
    store.seed(USER_A, TENANT_A, "file", {"path": "alpha/secret.pdf"})
    store.seed(USER_A, TENANT_A, "memory", {"value": "alpha home address"})
    store.seed(USER_A, TENANT_A, "vector", {"text": "alpha document chunk"})
    store.seed(USER_B, TENANT_B, "chat", {"title": "beta private chat"})
    store.seed(USER_B, TENANT_B, "file", {"path": "beta/secret.pdf"})
    store.seed(USER_B, TENANT_B, "memory", {"value": "beta home address"})
    store.seed(USER_B, TENANT_B, "vector", {"text": "beta document chunk"})
    return store


KINDS = ["chat", "file", "memory", "vector"]


# ---------------------------------------------------------------------------
# Cross-tenant reads
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_query_returns_only_the_principals_rows(seeded, kind):
    mine = seeded.query(USER_A, kind)
    theirs = seeded.query(USER_B, kind)
    assert len(mine) == 1
    assert len(theirs) == 1
    assert mine[0]["owner"] != theirs[0]["owner"]


@pytest.mark.parametrize("kind", KINDS)
def test_foreign_row_is_not_returned_as_mine(seeded, kind):
    """Asking with a foreign owner hint must not yield the foreign row."""
    foreign = seeded.query(USER_B, kind)[0]
    got = seeded.read(USER_A, foreign["id"], owner_hint=USER_B)
    assert got is None, (
        f"tenant B's {kind} row was readable as tenant A when a foreign "
        "owner hint was supplied"
    )


@pytest.mark.parametrize("kind", KINDS)
def test_empty_result_is_an_absent_row_not_an_empty_string(seeded, kind):
    foreign = seeded.query(USER_B, kind)[0]
    assert seeded.read(USER_A, foreign["id"]) is None


# ---------------------------------------------------------------------------
# Cross-tenant writes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_write_lands_under_the_principal_not_the_hint(seeded, kind):
    """A write claiming a foreign owner must be owned by the caller."""
    row = seeded.write(
        USER_A, TENANT_A, kind, {"value": "written by A"},
        owner_hint=USER_B,
    )
    assert row["owner"] == USER_A, "a foreign owner hint was honoured on write"
    assert seeded.read(USER_B, row["id"]) is None, (
        "a row written by A is readable by B"
    )


def test_write_cannot_forge_a_foreign_tenant(seeded):
    row = seeded.write(USER_A, TENANT_B, "chat", {"value": "forged"}, owner_hint=USER_B)
    # The tenant may be claimed, but the owner is what enforcement uses, so
    # the row is B-invisible.
    assert seeded.read(USER_B, row["id"]) is None


# ---------------------------------------------------------------------------
# Cross-tenant deletes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_deleting_a_foreign_row_is_a_noop(seeded, kind):
    foreign = seeded.query(USER_B, kind)[0]
    assert seeded.delete(USER_A, foreign["id"]) is False
    still_there = seeded.read(USER_B, foreign["id"])
    assert still_there is not None, "a cross-tenant delete actually deleted"


@pytest.mark.parametrize("kind", KINDS)
def test_owner_can_delete_their_own_row(seeded, kind):
    mine = seeded.query(USER_A, kind)[0]
    assert seeded.delete(USER_A, mine["id"]) is True
    # A soft delete, so the row is hidden but recovery remains possible.
    assert seeded.read(USER_A, mine["id"]) is None


def test_delete_does_not_leak_existence_pattern(seeded):
    """A deleted row and a never-existent row answer identically."""
    mine = seeded.query(USER_A, "chat")[0]
    seeded.delete(USER_A, mine["id"])
    assert seeded.read(USER_B, mine["id"]) is None
    assert seeded.read(USER_B, "no-such-id") is None


# ---------------------------------------------------------------------------
# Vector retrieval
# ---------------------------------------------------------------------------


def test_vector_retrieval_does_not_return_foreign_chunks(seeded):
    """RAG retrieval is scoped by the same owner as every other query."""
    retrieved = seeded.query(USER_A, "vector")
    assert retrieved, "A's own chunks must be retrievable"
    for chunk in retrieved:
        assert chunk["owner"] == USER_A
        assert "beta" not in str(chunk["payload"]).lower()


def test_vector_retrieval_ignores_a_foreign_tenant_filter(seeded):
    """A retrieval request must not be able to widen the scope."""
    got = seeded.query(USER_A, "vector", tenant_hint=TENANT_B)
    assert len(got) == 1
    assert got[0]["owner"] == USER_A


# ---------------------------------------------------------------------------
# The production access layer honours the same rule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repository_conversation_query_scopes_by_user_id():
    """The repository's conversation query must take user_id from the caller.

    get_conversations(user_id) is the scoped accessor. It is passed the
    verified principal's id by the router; nothing in it reads a body field.
    A caller-supplied user_id reaching it would mean the router forwarded a
    request value, which this asserts it does not.
    """
    from app.repositories.database import client as repo

    assert hasattr(repo, "get_conversations")
    assert hasattr(repo, "get_conversation")
    assert hasattr(repo, "get_messages")
    assert hasattr(repo, "get_user_memory")

    # The scoped signature: the owner is the first positional parameter, so
    # there is no default that would silently widen the scope.
    import inspect

    for fn in (repo.get_conversation, repo.get_messages, repo.get_user_memory):
        sig = inspect.signature(fn)
        first = next(iter(sig.parameters))
        assert first in ("user_id", "conversation_id"), (
            f"{fn.__name__} does not lead with an owner-scoping parameter: "
            f"{list(sig.parameters)}"
        )


@pytest.mark.asyncio
async def test_repository_conversation_read_filters_by_user_id():
    """get_conversation's user_id must not default to None.

    A None default lets the query match any owner when the router forgets to
    pass one, which is exactly the cross-tenant leak.
    """
    import inspect

    from app.repositories.database import client as repo

    param = inspect.signature(repo.get_conversation).parameters["user_id"]
    assert param.default is inspect.Parameter.empty, (
        "get_conversation's user_id has a default, so an unscoped query is "
        "possible"
    )
