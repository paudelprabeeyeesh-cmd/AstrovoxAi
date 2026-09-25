"""add stripe_events idempotency table

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
        CREATE TABLE IF NOT EXISTS stripe_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            processed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_stripe_events_event_id ON stripe_events(event_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_stripe_events_event_id")
    op.execute("DROP TABLE IF EXISTS stripe_events")
