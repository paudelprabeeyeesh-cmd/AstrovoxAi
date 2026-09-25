#!/usr/bin/env python3
"""Seed sample data for development."""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL is not set")
        return
    with get_db() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(
            """
            INSERT INTO users (id, email, name, plan, email_verified)
            VALUES ('user-1', 'test@example.com', 'Test User', 'free', true)
            ON CONFLICT (email) DO NOTHING
            """
        )
        conn.execute(
            """
            INSERT INTO conversations (id, user_id, title)
            VALUES ('conv-1', 'user-1', 'Sample Conversation')
            ON CONFLICT (id) DO NOTHING
            """
        )
    logger.info("Seed data created")


if __name__ == "__main__":
    seed()
