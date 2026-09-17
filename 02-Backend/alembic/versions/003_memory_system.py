"""memory system with pgvector

Revision ID: 003
Revises: 002
Create Date: 2026-09-16

"""
from typing import Sequence, Union
from alembic import op

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        ALTER TABLE memories
        ALTER COLUMN embedding TYPE vector(1536)
        USING NULL
    """)
    op.execute("""
        ALTER TABLE memories
        ADD COLUMN IF NOT EXISTS memory_type TEXT,
        ADD COLUMN IF NOT EXISTS importance_score REAL DEFAULT 0.5
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_embedding
        ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_memories_embedding")
    op.execute("""
        ALTER TABLE memories
        DROP COLUMN IF EXISTS importance_score,
        DROP COLUMN IF EXISTS memory_type
    """)
    op.execute("""
        ALTER TABLE memories
        ALTER COLUMN embedding TYPE TEXT
    """)
