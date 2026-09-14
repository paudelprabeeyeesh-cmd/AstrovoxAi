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
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Refresh tokens
    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            token_hash TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Interactions
    op.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            session_id TEXT,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            agent_type TEXT,
            model TEXT NOT NULL,
            tokens INTEGER NOT NULL,
            cost REAL NOT NULL,
            latency_ms INTEGER,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            correction TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Documents
    op.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            title TEXT,
            content TEXT NOT NULL,
            embedding vector(1536),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS interactions")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
    op.execute("DROP TABLE IF EXISTS users")