"""ai orchestration tables

Revision ID: 014
Revises: 013
Create Date: 2026-09-24
"""
from typing import Sequence, Union
from alembic import op

revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS model_routing_decisions (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            task_type TEXT,
            selected_model TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            fallback_chain TEXT,
            estimated_cost_usd REAL,
            estimated_latency_ms INTEGER,
            confidence REAL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS reasoning_traces (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            events TEXT NOT NULL,
            reasoning_chain TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            final_response TEXT,
            duration_ms INTEGER,
            created_at TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS context_compression_jobs (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            original_text TEXT NOT NULL,
            compressed_text TEXT NOT NULL,
            original_tokens INTEGER NOT NULL,
            compressed_tokens INTEGER NOT NULL,
            strategy TEXT NOT NULL,
            compression_ratio REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS self_correction_passes (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            original_response TEXT NOT NULL,
            corrected_response TEXT NOT NULL,
            issues TEXT NOT NULL,
            passes INTEGER NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_model_routing_user ON model_routing_decisions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reasoning_traces_user ON reasoning_traces(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_compression_jobs_user ON context_compression_jobs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_self_correction_user ON self_correction_passes(user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_self_correction_user")
    op.execute("DROP INDEX IF EXISTS idx_compression_jobs_user")
    op.execute("DROP INDEX IF EXISTS idx_reasoning_traces_user")
    op.execute("DROP INDEX IF EXISTS idx_model_routing_user")
    op.execute("DROP TABLE IF EXISTS self_correction_passes")
    op.execute("DROP TABLE IF EXISTS context_compression_jobs")
    op.execute("DROP TABLE IF EXISTS reasoning_traces")
    op.execute("DROP TABLE IF EXISTS model_routing_decisions")
