"""Database module compatibility shim.

Provides init_db and related symbols expected by tests and legacy imports.
Functions are wrapped so tests can patch ``app.database.supabase``.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

supabase = None

try:
    from app.repositories.database.client import (  # noqa: F401
        ALLOWED_PROFILE_FIELDS,
        ALLOWED_CONVERSATION_FIELDS,
        ALLOWED_SETTINGS_FIELDS,
    )

    def init_db() -> None:  # type: ignore[misc]
        pass

    def get_db() -> Any:  # type: ignore[misc]
        raise RuntimeError("Database not available")

except Exception:  # pragma: no cover
    ALLOWED_PROFILE_FIELDS = {"full_name", "avatar_url", "bio", "website"}
    ALLOWED_CONVERSATION_FIELDS = {"title", "model", "folder_id", "is_pinned", "is_shared", "shared_at", "shared_with"}
    ALLOWED_SETTINGS_FIELDS = {"theme", "language", "notifications_enabled", "default_model", "voice_enabled"}

    def init_db() -> None:  # type: ignore[misc]
        logger.debug("init_db called with fallback shim")

    def get_db() -> Any:  # type: ignore[misc]
        raise RuntimeError("Database not available")


def _get_supabase():
    return sys.modules.get("app.database", sys.modules.get(__name__)).supabase


def get_user_profile(user_id: str):
    sb = _get_supabase()
    if sb is None:
        return None
    try:
        response = sb.table("profiles").select("*").eq("id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error fetching user profile: %s", e)
        return None


def create_user_profile(user_id: str, username: str, **kwargs):
    sb = _get_supabase()
    if sb is None:
        return None
    try:
        response = sb.table("profiles").insert({"id": user_id, "username": username, **kwargs}).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error creating user profile: %s", e)
        return None


def update_user_profile(user_id: str, **kwargs):
    sb = _get_supabase()
    if sb is None:
        return None
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_PROFILE_FIELDS}
    if not safe_kwargs:
        return None
    try:
        response = sb.table("profiles").update(safe_kwargs).eq("id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error updating user profile: %s", e)
        return None


def create_conversation(user_id: str, title: str = None, model: str = "gpt-4"):
    sb = _get_supabase()
    if sb is None:
        return None
    try:
        response = sb.table("conversations").insert({"user_id": user_id, "title": title or "New Conversation", "model": model}).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error creating conversation: %s", e)
        return None


def get_conversations(user_id: str):
    sb = _get_supabase()
    if sb is None:
        return []
    try:
        response = sb.table("conversations").select("*").eq("user_id", user_id).eq("is_deleted", False).order("updated_at", desc=True).execute()
        return response.data
    except Exception as e:
        logger.error("Error fetching conversations: %s", e)
        return []


def get_conversation(conversation_id: int, user_id: str = None):
    sb = _get_supabase()
    if sb is None:
        return None
    try:
        query = sb.table("conversations").select("*").eq("id", conversation_id)
        if user_id:
            query = query.eq("user_id", user_id)
        response = query.execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error fetching conversation: %s", e)
        return None


def update_conversation(conversation_id: int, **kwargs):
    sb = _get_supabase()
    if sb is None:
        return None
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_CONVERSATION_FIELDS}
    if not safe_kwargs:
        return None
    try:
        response = sb.table("conversations").update(safe_kwargs).eq("id", conversation_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error updating conversation: %s", e)
        return None


def delete_conversation(conversation_id: int):
    sb = _get_supabase()
    if sb is None:
        return False
    try:
        sb.table("conversations").update({"is_deleted": True}).eq("id", conversation_id).execute()
        return True
    except Exception as e:
        logger.error("Error deleting conversation: %s", e)
        return False


def create_message(conversation_id: int, user_id: str, role: str, content: str, **kwargs):
    sb = _get_supabase()
    if sb is None:
        return None
    try:
        response = sb.table("messages").insert({"conversation_id": conversation_id, "user_id": user_id, "role": role, "content": content, **kwargs}).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error creating message: %s", e)
        return None


def get_messages(conversation_id: int, limit: int = 100, offset: int = 0):
    sb = _get_supabase()
    if sb is None:
        return []
    try:
        response = sb.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).range(offset, offset + limit - 1).execute()
        return response.data
    except Exception as e:
        logger.error("Error fetching messages: %s", e)
        return []


def get_recent_messages(conversation_id: int, limit: int = 10):
    sb = _get_supabase()
    if sb is None:
        return []
    try:
        response = sb.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error("Error fetching recent messages: %s", e)
        return []


def save_memory(user_id: str, content: str, importance: int = 1):
    sb = _get_supabase()
    if sb is None:
        return None
    try:
        response = sb.table("ai_memory").insert({"user_id": user_id, "content": content, "importance": importance}).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error saving memory: %s", e)
        return None


def get_user_memory(user_id: str, limit: int = 50):
    sb = _get_supabase()
    if sb is None:
        return []
    try:
        response = sb.table("ai_memory").select("*").eq("user_id", user_id).order("importance", desc=True).order("created_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error("Error fetching memory: %s", e)
        return []


def get_user_settings(user_id: str):
    sb = _get_supabase()
    if sb is None:
        return None
    try:
        response = sb.table("user_settings").select("*").eq("user_id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error fetching settings: %s", e)
        return None


def update_user_settings(user_id: str, **kwargs):
    sb = _get_supabase()
    if sb is None:
        return None
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_SETTINGS_FIELDS}
    if not safe_kwargs:
        return None
    try:
        response = sb.table("user_settings").update(safe_kwargs).eq("user_id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error updating settings: %s", e)
        return None
