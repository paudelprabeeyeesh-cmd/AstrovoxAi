"""enterprise tables

Revision ID: 008
Revises: 007
Create Date: 2026-09-17

"""
from typing import Sequence, Union
from alembic import op

revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS organization_members (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT DEFAULT 'member',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_organization_members_org ON organization_members(org_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_organization_members_user ON organization_members(user_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_organization_members_unique ON organization_members(org_id, user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS workspace_members (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT DEFAULT 'member',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace ON workspace_members(workspace_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_members(user_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_members_unique ON workspace_members(workspace_id, user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS invitations (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT DEFAULT 'member',
            token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS sso_connections (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            provider_type TEXT NOT NULL,
            config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS sso_users (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            email TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_sso_users_org ON sso_users(org_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sso_users_email ON sso_users(email)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_sso_users_email")
    op.execute("DROP INDEX IF EXISTS idx_sso_users_org")
    op.execute("DROP TABLE IF EXISTS sso_users")
    op.execute("DROP TABLE IF EXISTS sso_connections")
    op.execute("DROP INDEX IF EXISTS idx_invitations_token")
    op.execute("DROP TABLE IF EXISTS invitations")
    op.execute("DROP UNIQUE INDEX IF EXISTS idx_workspace_members_unique")
    op.execute("DROP INDEX IF EXISTS idx_workspace_members_user")
    op.execute("DROP INDEX IF EXISTS idx_workspace_members_workspace")
    op.execute("DROP TABLE IF EXISTS workspace_members")
    op.execute("DROP TABLE IF EXISTS workspaces")
    op.execute("DROP UNIQUE INDEX IF EXISTS idx_organization_members_unique")
    op.execute("DROP INDEX IF EXISTS idx_organization_members_user")
    op.execute("DROP INDEX IF EXISTS idx_organization_members_org")
    op.execute("DROP TABLE IF EXISTS organization_members")
    op.execute("DROP TABLE IF EXISTS organizations")
