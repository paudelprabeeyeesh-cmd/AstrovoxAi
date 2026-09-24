"""finetuning pipeline tables

Revision ID: 012
Revises: 011
Create Date: 2026-09-24

"""
from typing import Sequence, Union
from alembic import op

revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS finetuning_jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            model TEXT NOT NULL,
            training_file TEXT NOT NULL,
            validation_file TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            fine_tuned_model TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            trained_tokens INTEGER DEFAULT 0
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS training_datasets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_type TEXT NOT NULL,
            size INTEGER NOT NULL,
            path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'uploaded',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS model_registry_entries (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            provider TEXT NOT NULL,
            model_id TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'development',
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_finetuning_user ON finetuning_jobs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_training_datasets_user ON training_datasets(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_model_registry_name ON model_registry_entries(name)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_model_registry_name")
    op.execute("DROP INDEX IF EXISTS idx_training_datasets_user")
    op.execute("DROP INDEX IF EXISTS idx_finetuning_user")
    op.execute("DROP TABLE IF EXISTS model_registry_entries")
    op.execute("DROP TABLE IF EXISTS training_datasets")
    op.execute("DROP TABLE IF EXISTS finetuning_jobs")
