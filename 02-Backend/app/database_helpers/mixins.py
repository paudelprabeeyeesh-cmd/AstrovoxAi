"""SQLAlchemy mixins for common data-layer patterns."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class SoftDeleteMixin:
    """Mixin that adds soft-delete support via `is_deleted` and `deleted_at` columns."""

    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True)

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None


class AuditColumnsMixin:
    """Mixin that adds audit trail columns."""

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(default=None, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(default=None, nullable=True)
