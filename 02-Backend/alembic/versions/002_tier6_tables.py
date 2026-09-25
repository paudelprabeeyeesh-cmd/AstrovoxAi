"""add tier 6 tables

Revision ID: 002
Revises: 001
Create Date: 2026-09-15

"""
from typing import Sequence, Union
from alembic import op

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            properties TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS rag_evaluations (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            retrieved_ids TEXT NOT NULL,
            golden_ids TEXT NOT NULL,
            recall_at_5 REAL NOT NULL,
            faithfulness_score REAL NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            hypothesis TEXT NOT NULL,
            variants TEXT NOT NULL,
            traffic_split TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS experiment_assignments (
            id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            variant TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS experiment_results (
            id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            variant TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON analytics_events(event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_evaluations_query ON rag_evaluations(query)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiments_owner ON experiments(owner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiment_results_exp ON experiment_results(experiment_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_experiment_results_exp")
    op.execute("DROP INDEX IF EXISTS idx_experiments_owner")
    op.execute("DROP INDEX IF EXISTS idx_rag_evaluations_query")
    op.execute("DROP INDEX IF EXISTS idx_analytics_events_type")
    op.execute("DROP TABLE IF EXISTS experiment_results")
    op.execute("DROP TABLE IF EXISTS experiment_assignments")
    op.execute("DROP TABLE IF EXISTS experiments")
    op.execute("DROP TABLE IF EXISTS rag_evaluations")
    op.execute("DROP TABLE IF EXISTS analytics_events")
