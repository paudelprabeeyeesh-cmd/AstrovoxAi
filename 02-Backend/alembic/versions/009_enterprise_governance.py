"""enterprise governance tables

Revision ID: 009
Revises: 008
Create Date: 2026-09-25

"""
from typing import Sequence, Union
from alembic import op

revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS tenant_configs (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            is_active INTEGER DEFAULT 1,
            settings TEXT,
            data_residency TEXT DEFAULT 'default',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_tenant_configs_tenant ON tenant_configs(tenant_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            country TEXT DEFAULT '',
            data_residency_required INTEGER DEFAULT 0,
            compliance_frameworks TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_regions_code ON regions(code)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS org_residency (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL UNIQUE,
            region_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_residency_org ON org_residency(org_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_exports (
            id TEXT PRIMARY KEY,
            requester_id TEXT NOT NULL,
            format TEXT NOT NULL,
            filters TEXT,
            status TEXT DEFAULT 'pending',
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_exports_requester ON audit_exports(requester_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS retention_policies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            retention_days INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            action TEXT DEFAULT 'delete',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_retention_policies_type ON retention_policies(data_type)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS billing_meters (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL,
            cost REAL NOT NULL DEFAULT 0,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_billing_meters_tenant ON billing_meters(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_billing_meters_user ON billing_meters(user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_quotas (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            limit_value REAL NOT NULL,
            period TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_quotas_tenant ON usage_quotas(tenant_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_quotas_unique ON usage_quotas(tenant_id, user_id, resource_type, period)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'open',
            category TEXT DEFAULT 'general',
            assigned_to TEXT,
            tags TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_tenant ON support_tickets(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS partner_accounts (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            name TEXT NOT NULL,
            api_key TEXT NOT NULL UNIQUE,
            scopes TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_partner_accounts_tenant ON partner_accounts(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_partner_accounts_api_key ON partner_accounts(api_key)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS export_import_jobs (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            job_type TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            filters TEXT,
            format TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            file_path TEXT,
            error_message TEXT,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_export_import_jobs_tenant ON export_import_jobs(tenant_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_export_import_jobs_tenant")
    op.execute("DROP TABLE IF EXISTS export_import_jobs")
    op.execute("DROP INDEX IF EXISTS idx_partner_accounts_api_key")
    op.execute("DROP INDEX IF EXISTS idx_partner_accounts_tenant")
    op.execute("DROP TABLE IF EXISTS partner_accounts")
    op.execute("DROP INDEX IF EXISTS idx_support_tickets_status")
    op.execute("DROP INDEX IF EXISTS idx_support_tickets_tenant")
    op.execute("DROP TABLE IF EXISTS support_tickets")
    op.execute("DROP INDEX IF EXISTS idx_usage_quotas_unique")
    op.execute("DROP INDEX IF EXISTS idx_usage_quotas_tenant")
    op.execute("DROP TABLE IF EXISTS usage_quotas")
    op.execute("DROP INDEX IF EXISTS idx_billing_meters_user")
    op.execute("DROP INDEX IF EXISTS idx_billing_meters_tenant")
    op.execute("DROP TABLE IF EXISTS billing_meters")
    op.execute("DROP INDEX IF EXISTS idx_retention_policies_type")
    op.execute("DROP TABLE IF EXISTS retention_policies")
    op.execute("DROP INDEX IF EXISTS idx_audit_exports_requester")
    op.execute("DROP TABLE IF EXISTS audit_exports")
    op.execute("DROP INDEX IF EXISTS idx_org_residency_org")
    op.execute("DROP TABLE IF EXISTS org_residency")
    op.execute("DROP INDEX IF EXISTS idx_regions_code")
    op.execute("DROP TABLE IF EXISTS regions")
    op.execute("DROP INDEX IF EXISTS idx_tenant_configs_tenant")
    op.execute("DROP TABLE IF EXISTS tenant_configs")
