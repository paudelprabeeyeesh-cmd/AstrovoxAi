"""Database module compatibility shim.

Provides init_db and related symbols expected by tests and legacy imports.
Real implementations live in app.infrastructure.database and app.database_engine.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from app.infrastructure.database import DatabaseEngine, get_database  # noqa: F401
    from app.repositories.database.client import (
        get_user_profile,
        create_user_profile,
        update_user_profile,
        create_conversation,
        get_conversations,
        get_conversation,
        update_conversation,
        delete_conversation,
        create_message,
        get_messages,
        get_recent_messages,
        save_memory,
        get_user_memory,
        get_user_settings,
        update_user_settings,
        ALLOWED_PROFILE_FIELDS,
        ALLOWED_CONVERSATION_FIELDS,
        ALLOWED_SETTINGS_FIELDS,
    )

    _db = get_database()

    def init_db() -> None:  # type: ignore[misc]
        try:
            _db.health_check()
        except Exception:
            pass

    def get_db() -> Any:  # type: ignore[misc]
        return _db.get_session()

except Exception:  # pragma: no cover
    def init_db() -> None:  # type: ignore[misc]
        logger.debug("init_db called with fallback shim")

    def get_db() -> Any:  # type: ignore[misc]
        raise RuntimeError("Database not available")
