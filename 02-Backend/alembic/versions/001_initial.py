"""initial migration

Revision ID: 001
Revises: 
Create Date: 2026-09-14

"""
from typing import Sequence, Union
from alembic import op

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            email_verified INTEGER DEFAULT 0,
            plan TEXT DEFAULT 'free',
            stripe_customer_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id TEXT PRIMARY KEY,
            ip TEXT NOT NULL,
            success INTEGER DEFAULT 0,
            lockout_until TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            prompt TEXT NOT NULL,
            variables TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            template_id TEXT,
            cron TEXT NOT NULL,
            email TEXT NOT NULL,
            last_run TIMESTAMP,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_docs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            style_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            steps TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS tools (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            request_id TEXT,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ab_tests (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            variants TEXT NOT NULL,
            traffic_split REAL NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ab_assignments (
            id TEXT PRIMARY KEY,
            test_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            variant TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            tokens INTEGER NOT NULL,
            cost REAL NOT NULL,
            model TEXT NOT NULL,
            cached INTEGER DEFAULT 0,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            plan TEXT NOT NULL,
            amount REAL NOT NULL,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT DEFAULT 'member',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            name TEXT,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS marketplace_prompts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            prompt TEXT NOT NULL,
            price REAL DEFAULT 0,
            downloads INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS addons (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            stripe_price_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ipo_metrics (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            target TEXT NOT NULL,
            current TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            signup_user_id TEXT,
            signup_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS integrations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT DEFAULT 'founder',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            post_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS amas (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            scheduled_at TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS case_studies (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS outreach (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            template_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            recipient_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ad_campaigns (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            platform TEXT NOT NULL,
            budget REAL NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS affiliates (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            conversions INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS enterprise_accounts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            company TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            plan TEXT DEFAULT 'enterprise',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS sso_connections (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS enterprise_audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS slas (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            tier TEXT NOT NULL,
            uptime_guarantee REAL NOT NULL,
            response_time_hours INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS custom_models (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS verticals (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS sdk_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ma_targets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            valuation REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            model TEXT NOT NULL,
            tokens INTEGER NOT NULL,
            cost REAL NOT NULL,
            latency_ms INTEGER,
            rating INTEGER,
            correction TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS interaction_labels (
            id TEXT PRIMARY KEY,
            interaction_id TEXT NOT NULL,
            label TEXT NOT NULL,
            notes TEXT,
            labeled_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_templates_user ON templates(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_schedules_user ON schedules(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_user ON knowledge_docs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflows_user ON workflows(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tools_user ON tools(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON usage(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_teams_user ON teams(owner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_marketplace_user ON marketplace_prompts(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_addons_user ON addons(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_referrals_user ON referrals(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals(code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_integrations_user ON integrations(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_amas_scheduled ON amas(scheduled_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_case_studies_user ON case_studies(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_outreach_user ON outreach(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON ad_campaigns(start_date, end_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_affiliates_code ON affiliates(code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sso_user ON sso_connections(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_enterprise_audit_user ON enterprise_audit_logs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_slas_account ON slas(account_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_custom_models_user ON custom_models(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_verticals_name ON verticals(name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_regions_code ON regions(code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sdk_keys_user ON sdk_keys(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ma_targets_name ON ma_targets(name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ipo_metrics_name ON ipo_metrics(name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_posts_user")
    op.execute("DROP INDEX IF EXISTS idx_interactions_user")
    op.execute("DROP INDEX IF EXISTS idx_ipo_metrics_name")
    op.execute("DROP INDEX IF EXISTS idx_ma_targets_name")
    op.execute("DROP INDEX IF EXISTS idx_sdk_keys_user")
    op.execute("DROP INDEX IF EXISTS idx_regions_code")
    op.execute("DROP INDEX IF EXISTS idx_verticals_name")
    op.execute("DROP INDEX IF EXISTS idx_custom_models_user")
    op.execute("DROP INDEX IF EXISTS idx_slas_account")
    op.execute("DROP INDEX IF EXISTS idx_enterprise_audit_user")
    op.execute("DROP INDEX IF EXISTS idx_sso_user")
    op.execute("DROP INDEX IF EXISTS idx_affiliates_code")
    op.execute("DROP INDEX IF EXISTS idx_campaigns_dates")
    op.execute("DROP INDEX IF EXISTS idx_outreach_user")
    op.execute("DROP INDEX IF EXISTS idx_case_studies_user")
    op.execute("DROP INDEX IF EXISTS idx_amas_scheduled")
    op.execute("DROP INDEX IF EXISTS idx_comments_post")
    op.execute("DROP INDEX IF EXISTS idx_integrations_user")
    op.execute("DROP INDEX IF EXISTS idx_referrals_code")
    op.execute("DROP INDEX IF EXISTS idx_referrals_user")
    op.execute("DROP INDEX IF EXISTS idx_audit_user")
    op.execute("DROP INDEX IF EXISTS idx_addons_user")
    op.execute("DROP INDEX IF EXISTS idx_marketplace_user")
    op.execute("DROP INDEX IF EXISTS idx_api_keys_user")
    op.execute("DROP INDEX IF EXISTS idx_team_members_team")
    op.execute("DROP INDEX IF EXISTS idx_teams_user")
    op.execute("DROP INDEX IF EXISTS idx_subscriptions_user")
    op.execute("DROP INDEX IF EXISTS idx_usage_user")
    op.execute("DROP INDEX IF EXISTS idx_feedback_user")
    op.execute("DROP INDEX IF EXISTS idx_tools_user")
    op.execute("DROP INDEX IF EXISTS idx_workflows_user")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_user")
    op.execute("DROP INDEX IF EXISTS idx_schedules_user")
    op.execute("DROP INDEX IF EXISTS idx_templates_user")
    op.execute("DROP INDEX IF EXISTS idx_conversations_user")
    op.execute("DROP INDEX IF EXISTS idx_messages_conversation")
    op.execute("DROP INDEX IF EXISTS idx_memories_user")
    op.execute("DROP TABLE IF EXISTS interaction_labels")
    op.execute("DROP TABLE IF EXISTS interactions")
    op.execute("DROP TABLE IF EXISTS ma_targets")
    op.execute("DROP TABLE IF EXISTS sdk_keys")
    op.execute("DROP TABLE IF EXISTS regions")
    op.execute("DROP TABLE IF EXISTS verticals")
    op.execute("DROP TABLE IF EXISTS custom_models")
    op.execute("DROP TABLE IF EXISTS slas")
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS enterprise_audit_logs")
    op.execute("DROP TABLE IF EXISTS sso_connections")
    op.execute("DROP TABLE IF EXISTS enterprise_accounts")
    op.execute("DROP TABLE IF EXISTS affiliates")
    op.execute("DROP TABLE IF EXISTS ad_campaigns")
    op.execute("DROP TABLE IF EXISTS outreach")
    op.execute("DROP TABLE IF EXISTS case_studies")
    op.execute("DROP TABLE IF EXISTS amas")
    op.execute("DROP TABLE IF EXISTS comments")
    op.execute("DROP TABLE IF EXISTS posts")
    op.execute("DROP TABLE IF EXISTS integrations")
    op.execute("DROP TABLE IF EXISTS referrals")
    op.execute("DROP TABLE IF EXISTS ipo_metrics")
    op.execute("DROP TABLE IF EXISTS addons")
    op.execute("DROP TABLE IF EXISTS marketplace_prompts")
    op.execute("DROP TABLE IF EXISTS api_keys")
    op.execute("DROP TABLE IF EXISTS team_members")
    op.execute("DROP TABLE IF EXISTS teams")
    op.execute("DROP TABLE IF EXISTS subscriptions")
    op.execute("DROP TABLE IF EXISTS usage")
    op.execute("DROP TABLE IF EXISTS ab_assignments")
    op.execute("DROP TABLE IF EXISTS ab_tests")
    op.execute("DROP TABLE IF EXISTS feedback")
    op.execute("DROP TABLE IF EXISTS tools")
    op.execute("DROP TABLE IF EXISTS workflows")
    op.execute("DROP TABLE IF EXISTS user_profiles")
    op.execute("DROP TABLE IF EXISTS knowledge_docs")
    op.execute("DROP TABLE IF EXISTS schedules")
    op.execute("DROP TABLE IF EXISTS templates")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS conversations")
    op.execute("DROP TABLE IF EXISTS memories")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
    op.execute("DROP TABLE IF EXISTS login_attempts")
    op.execute("DROP TABLE IF EXISTS users")
