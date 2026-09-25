"""advanced analytics tables

Revision ID: 010
Revises: 009
Create Date: 2026-09-25

"""
from typing import Sequence, Union
from alembic import op

revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS ab_events (
            id TEXT PRIMARY KEY,
            test_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            variant TEXT NOT NULL,
            event_name TEXT NOT NULL,
            event_value REAL,
            properties TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ab_events_test ON ab_events(test_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS funnels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            steps TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS funnel_events (
            id TEXT PRIMARY KEY,
            funnel_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            session_id TEXT,
            step_index INTEGER NOT NULL,
            step_name TEXT NOT NULL,
            entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            exited_at TIMESTAMP,
            completed INTEGER DEFAULT 0,
            drop_off_reason TEXT,
            properties TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_funnel_events_funnel ON funnel_events(funnel_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS cohorts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            definition TEXT NOT NULL,
            member_count INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS cohort_members (
            id TEXT PRIMARY KEY,
            cohort_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            left_at TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cohort_members_cohort ON cohort_members(cohort_id)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS cohort_metrics (
            id TEXT PRIMARY KEY,
            cohort_id TEXT NOT NULL,
            date TEXT NOT NULL,
            active_users INTEGER DEFAULT 0,
            new_retained INTEGER DEFAULT 0,
            returning_users INTEGER DEFAULT 0,
            churned_users INTEGER DEFAULT 0,
            retention_rate REAL DEFAULT 0,
            revenue REAL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cohort_metrics_cohort_date ON cohort_metrics(cohort_id, date)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS retention_snapshots (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            cohort_date TEXT NOT NULL,
            day_0 INTEGER DEFAULT 1,
            day_1 INTEGER DEFAULT 0,
            day_3 INTEGER DEFAULT 0,
            day_7 INTEGER DEFAULT 0,
            day_14 INTEGER DEFAULT 0,
            day_30 INTEGER DEFAULT 0,
            day_60 INTEGER DEFAULT 0,
            day_90 INTEGER DEFAULT 0,
            last_active_date TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_retention_user_cohort ON retention_snapshots(user_id, cohort_date)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS revenue_events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            plan_name TEXT,
            plan_interval TEXT,
            payment_method TEXT,
            stripe_invoice_id TEXT,
            stripe_customer_id TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_revenue_user ON revenue_events(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_revenue_type ON revenue_events(event_type)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS custom_reports (
            id TEXT PRIMARY KEY,
            report_name TEXT NOT NULL,
            description TEXT,
            created_by TEXT NOT NULL,
            config TEXT NOT NULL,
            schedule TEXT,
            recipients TEXT DEFAULT '[]',
            last_run_at TIMESTAMP,
            is_public INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_custom_reports_owner ON custom_reports(created_by)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_custom_reports_owner")
    op.execute("DROP INDEX IF EXISTS idx_revenue_type")
    op.execute("DROP INDEX IF EXISTS idx_revenue_user")
    op.execute("DROP INDEX IF EXISTS idx_retention_user_cohort")
    op.execute("DROP INDEX IF EXISTS idx_cohort_metrics_cohort_date")
    op.execute("DROP INDEX IF EXISTS idx_cohort_members_cohort")
    op.execute("DROP INDEX IF EXISTS idx_funnel_events_funnel")
    op.execute("DROP INDEX IF EXISTS idx_ab_events_test")
    op.execute("DROP TABLE IF EXISTS custom_reports")
    op.execute("DROP TABLE IF EXISTS revenue_events")
    op.execute("DROP TABLE IF EXISTS retention_snapshots")
    op.execute("DROP TABLE IF EXISTS cohort_metrics")
    op.execute("DROP TABLE IF EXISTS cohort_members")
    op.execute("DROP TABLE IF EXISTS cohorts")
    op.execute("DROP TABLE IF EXISTS funnel_events")
    op.execute("DROP TABLE IF EXISTS funnels")
    op.execute("DROP TABLE IF EXISTS ab_events")
