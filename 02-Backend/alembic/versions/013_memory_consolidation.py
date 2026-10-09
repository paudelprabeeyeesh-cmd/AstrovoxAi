"""memory consolidation tables

Revision ID: 013
Revises: 012
Create Date: 2026-09-24
"""
from typing import Sequence, Union
from alembic import op

revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory_consolidation_entries (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            memory_id TEXT NOT NULL,
            action TEXT NOT NULL,
            source_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            importance_before REAL NOT NULL,
            importance_after REAL NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS consolidation_summaries (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            summary TEXT NOT NULL,
            source_message_count INTEGER NOT NULL,
            action TEXT NOT NULL DEFAULT 'created',
            created_at TEXT NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_consolidation_user_id ON memory_consolidation_entries(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_consolidation_summaries_user_id ON consolidation_summaries(user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_consolidation_summaries_user_id")
    op.execute("DROP INDEX IF EXISTS idx_consolidation_user_id")
    op.execute("DROP TABLE IF EXISTS consolidation_summaries")
    op.execute("DROP TABLE IF EXISTS memory_consolidation_entries")
