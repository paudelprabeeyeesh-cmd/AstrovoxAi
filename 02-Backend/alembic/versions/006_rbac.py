"""knowledge graph tables

Revision ID: 006
Revises: 005
Create Date: 2026-09-16

"""
from typing import Sequence, Union
from alembic import op

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_entities (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            name TEXT NOT NULL,
            properties TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_relationships (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_entities_type ON knowledge_entities(entity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_source ON knowledge_relationships(source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_target ON knowledge_relationships(target_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_knowledge_relationships_target")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_relationships_source")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_entities_type")
    op.execute("DROP TABLE IF EXISTS knowledge_relationships")
    op.execute("DROP TABLE IF EXISTS knowledge_entities")
