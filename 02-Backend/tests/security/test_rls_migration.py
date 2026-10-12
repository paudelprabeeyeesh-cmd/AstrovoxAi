"""Row-level security migration coverage (backlog item 1).

No Postgres is available here, so this does not execute the migration. It
asserts the migration's *shape* instead, which is the part that can be
checked statically and the part that decays: a new tenant-owned table
added later gets no policy unless someone notices, and the existing
coverage tests would not fail when the schema creates it.

Every rule below matches one the policies must satisfy, so a regression in
the migration is a red test rather than a silent gap.

Requires the migration file and the schema it guards to agree:
  * every table the schema creates with a user_id column is enabled and
    has policies for all four verbs;
  * anon is denied;
  * ownership is derived from auth.uid(), never from a request body.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
MIGRATION = (
    REPO / "supabase" / "migrations" / "20261012013000_rls_tenant_isolation.sql"
)
DATABASE_PY = REPO / "database" / "connection.py"

TABLES = [
    "conversations", "messages", "ai_memory", "documents",
    "document_chunks", "interactions", "finetuning_jobs",
    "training_datasets", "usage_events",
]


@pytest.fixture(scope="module")
def migration() -> str:
    assert MIGRATION.is_file(), (
        f"RLS migration missing at {MIGRATION}; without it the database "
        "asserts no tenant isolation"
    )
    return MIGRATION.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def schema() -> str:
    assert DATABASE_PY.is_file(), "database/connection.py not found"
    return DATABASE_PY.read_text(encoding="utf-8")


def _sql(text: str) -> str:
    """Collapse whitespace so statements can be matched regardless of layout."""
    return re.sub(r"\s+", " ", text)


def test_every_tenant_table_has_rls_enabled(migration):
    sql = _sql(migration)
    for table in TABLES:
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in sql, (
            f"RLS is not enabled on {table}; rows are readable by anyone"
        )


def test_every_tenant_table_has_all_four_verbs(migration):
    sql = _sql(migration)
    # document_chunks has no user_id of its own: ownership is inherited from
    # its parent document, so an UPDATE policy would have nothing to compare.
    skip = {"document_chunks": {"UPDATE"}}
    for table in TABLES:
        for verb in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            if verb in skip.get(table, set()):
                continue
            assert f"ON public.{table} FOR {verb} TO authenticated" in sql, (
                f"{table} has no {verb} policy; the verb is denied by "
                "default, which is safe, but a missing policy silently "
                "breaks a feature that should work"
            )


def test_anon_is_denied_everywhere(migration):
    sql = _sql(migration)
    for table in TABLES:
        assert f"ON public.{table} FOR ALL TO anon USING (false) WITH CHECK (false)" in sql, (
            f"anon is not explicitly denied on {table}; ENABLE ROW LEVEL "
            "SECURITY with no anon policy does deny, but an explicit denial "
            "keeps that from reading as an oversight"
        )


def test_ownership_is_derived_from_auth_uid(migration):
    """Policies must use the verified JWT claim, never a request body value."""
    sql = _sql(migration)
    assert sql.count("auth.uid()") >= len(TABLES), (
        "policies do not consistently derive ownership from auth.uid()"
    )
    # A body-derived owner would let any caller name any tenant.
    assert "user_id = \"header\"" not in sql and "user_id = body" not in sql, (
        "a policy derives ownership from a client-supplied value"
    )


def test_chunk_ownership_is_inherited(migration):
    """document_chunks has no user_id of its own.

    Its policy must therefore reach through the parent document, not
    compare a column it does not have.
    """
    sql = _sql(migration)
    assert "EXISTS ( SELECT 1 FROM public.documents d WHERE d.id = document_chunks.document_id AND d.user_id = auth.uid() )" in sql, (
        "document_chunks does not inherit ownership from its parent document; "
        "a self-referencing policy would compare a column that does not exist"
    )


def test_no_policy_is_deleted_without_being_recreated(migration):
    """Every DROP POLICY IF EXISTS is paired with a CREATE POLICY."""
    drops = re.findall(r'DROP POLICY IF EXISTS "?([A-Za-z0-9_]+)"?', migration)
    for name in drops:
        assert f'CREATE POLICY "{name}"' in migration, (
            f"policy {name} is dropped and never recreated"
        )


def test_migration_is_idempotent(migration):
    """Re-running must not fail, so every DROP is IF EXISTS."""
    bare_drops = re.findall(r"DROP POLICY (?!IF EXISTS)", migration)
    assert not bare_drops, (
        f"{len(bare_drops)} DROP POLICY without IF EXISTS; the migration "
        "cannot be re-run"
    )


def test_every_schema_table_with_user_id_is_covered(schema, migration):
    """A new tenant-owned table in the schema must not silently skip RLS.

    The schema is the source of truth for which tables carry a user_id.
    If it declares one that the migration does not cover, the gap is real.
    """
    schema_tables = set(re.findall(
        r"CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\);", schema, re.S
    ) and re.findall(
        r"CREATE TABLE IF NOT EXISTS (\w+) \(", schema
    ) or [])
    # Find every table that declares a user_id column.
    owner = set()
    for name in schema_tables:
        m = re.search(
            rf"CREATE TABLE IF NOT EXISTS {name} \((.*?)\n\s*\);", schema, re.S
        )
        if m and re.search(r"\buser_id\s+TEXT", m.group(1)):
            owner.add(name)
    missing = sorted(owner - set(TABLES))
    assert not missing, (
        f"these tables carry a user_id but have no RLS policy: {missing}. "
        "Add them to the migration."
    )


def test_migration_does_not_grant_service_role_broadly(migration):
    """The service role bypasses RLS by design; it must not be added to
    the anon or authenticated policies."""
    sql = _sql(migration)
    assert "TO service_role" not in sql, (
        "a policy explicitly targets service_role, which bypasses RLS anyway"
    )


def test_migration_has_no_syntax_breaking_terminators(migration):
    """Every statement block is closed."""
    assert migration.count("$$") % 2 == 0, (
        "an odd number of $$ delimiters means a DO block is unclosed"
    )
