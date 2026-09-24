"""authentication tables

Revision ID: 015
Revises: 014
Create Date: 2026-09-24

"""
from typing import Sequence, Union
from alembic import op

revision: str = '015'
down_revision: Union[str, None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_verification_user ON email_verification_tokens(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_verification_token ON email_verification_tokens(token_hash)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens(token_hash)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS mfa_secrets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            secret TEXT NOT NULL,
            enabled INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_mfa_secrets_user ON mfa_secrets(user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS mfa_backup_codes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_mfa_backup_codes_user ON mfa_backup_codes(user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            refresh_token TEXT NOT NULL UNIQUE,
            ip_address TEXT,
            user_agent TEXT,
            expires_at TEXT NOT NULL,
            last_activity_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh ON user_sessions(refresh_token)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            device_type TEXT DEFAULT 'unknown',
            platform TEXT,
            browser TEXT,
            fingerprint TEXT NOT NULL,
            last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
            trusted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_devices_fingerprint ON devices(fingerprint)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS magic_links (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            email TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            used INTEGER DEFAULT 0,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_magic_links_email ON magic_links(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_magic_links_token ON magic_links(token_hash)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS oauth_accounts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            access_token TEXT,
            refresh_token TEXT,
            expires_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(provider, provider_user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user ON oauth_accounts(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_oauth_accounts_provider ON oauth_accounts(provider, provider_user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_oauth_accounts_provider")
    op.execute("DROP INDEX IF EXISTS idx_oauth_accounts_user")
    op.execute("DROP TABLE IF EXISTS oauth_accounts")
    op.execute("DROP INDEX IF EXISTS idx_magic_links_token")
    op.execute("DROP INDEX IF EXISTS idx_magic_links_email")
    op.execute("DROP TABLE IF EXISTS magic_links")
    op.execute("DROP INDEX IF EXISTS idx_devices_fingerprint")
    op.execute("DROP INDEX IF EXISTS idx_devices_user")
    op.execute("DROP TABLE IF EXISTS devices")
    op.execute("DROP INDEX IF EXISTS idx_user_sessions_refresh")
    op.execute("DROP INDEX IF EXISTS idx_user_sessions_token")
    op.execute("DROP INDEX IF EXISTS idx_user_sessions_user")
    op.execute("DROP TABLE IF EXISTS user_sessions")
    op.execute("DROP INDEX IF EXISTS idx_mfa_backup_codes_user")
    op.execute("DROP TABLE IF EXISTS mfa_backup_codes")
    op.execute("DROP INDEX IF EXISTS idx_mfa_secrets_user")
    op.execute("DROP TABLE IF EXISTS mfa_secrets")
    op.execute("DROP INDEX IF EXISTS idx_password_reset_token")
    op.execute("DROP INDEX IF EXISTS idx_password_reset_user")
    op.execute("DROP TABLE IF EXISTS password_reset_tokens")
    op.execute("DROP INDEX IF EXISTS idx_email_verification_token")
    op.execute("DROP INDEX IF EXISTS idx_email_verification_user")
    op.execute("DROP TABLE IF EXISTS email_verification_tokens")
