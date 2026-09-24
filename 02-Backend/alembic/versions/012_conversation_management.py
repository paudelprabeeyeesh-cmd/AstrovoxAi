"""add conversation management fields

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
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS model TEXT DEFAULT 'gpt-4'
    """)
    op.execute("""
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS pinned INTEGER DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS archived INTEGER DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS folder TEXT
    """)
    op.execute("""
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_user_pinned ON conversations(user_id, pinned)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_user_archived ON conversations(user_id, archived)
    """)

    op.execute("""
        ALTER TABLE messages ADD COLUMN IF NOT EXISTS model_used TEXT
    """)
    op.execute("""
        ALTER TABLE messages ADD COLUMN IF NOT EXISTS tokens_used INTEGER
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_conversations_user_archived")
    op.execute("DROP INDEX IF EXISTS idx_conversations_user_pinned")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS folder")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS archived")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS pinned")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS model")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS tokens_used")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS model_used")
