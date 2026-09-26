"""Database engine with PostgreSQL and pgvector support."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import get_config

logger = logging.getLogger(__name__)


class DatabaseEngine:
    """PostgreSQL database engine with connection pooling."""

    def __init__(self) -> None:
        self._config = get_config()
        self._engine = None
        self._session_factory = None
        self._connect()

    def _connect(self) -> None:
        try:
            self._engine = create_engine(
                self._config.database.url,
                pool_size=self._config.database.pool_size,
                max_overflow=self._config.database.max_overflow,
                echo=self._config.database.echo,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            self._session_factory = sessionmaker(bind=self._engine)
            logger.info("Connected to database")
        except Exception as exc:
            logger.error(f"Database connection failed: {exc}")
            raise

    def get_session(self) -> Session:
        if not self._session_factory:
            raise RuntimeError("Database not initialized")
        return self._session_factory()

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        with self.get_session() as session:
            return session.execute(text(query), params or {})

    def health_check(self) -> bool:
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_replica_session(self) -> Session:
        """Get a session connected to a read replica."""
        if not hasattr(self._config, 'database_replica_url') or not self._config.database_replica_url:
            return self.get_session()
        try:
            replica_engine = create_engine(
                self._config.database_replica_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )
            return sessionmaker(bind=replica_engine)()
        except Exception as exc:
            logger.warning(f"Replica connection failed, using primary: {exc}")
            return self.get_session()


_db: Optional[DatabaseEngine] = None


def get_database() -> DatabaseEngine:
    global _db
    if _db is None:
        _db = DatabaseEngine()
    return _db
