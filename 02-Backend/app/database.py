from .logging_config import logger
from .supabase_client import get_supabase

supabase = get_supabase()


# User profile operations
async def get_user_profile(user_id: str):
    """Get user profile by ID"""
    try:
        response = supabase.table("profiles").select("*").eq("id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching user profile for user {user_id}: {e}", exc_info=True)
        return None


async def create_user_profile(
    user_id: str, username: str, full_name: str = None, avatar_url: str = None
):
    """Create user profile"""
    try:
        response = (
            supabase.table("profiles")
            .insert(
                {
                    "id": user_id,
                    "username": username,
                    "full_name": full_name,
                    "avatar_url": avatar_url,
                }
            )
            .execute()
        )
        logger.info(f"Created user profile for {user_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating user profile for {user_id}: {e}", exc_info=True)
        return None


async def update_user_profile(user_id: str, **kwargs):
    """Update user profile"""
    try:
        response = supabase.table("profiles").update(kwargs).eq("id", user_id).execute()
        logger.info(f"Updated user profile for {user_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating user profile for {user_id}: {e}", exc_info=True)
        return None


# Conversation operations
async def create_conversation(user_id: str, title: str = None, model: str = "gpt-4"):
    """Create a new conversation"""
    try:
        response = (
            supabase.table("conversations")
            .insert(
                {
                    "user_id": user_id,
                    "title": title or "New Conversation",
                    "model": model,
                }
            )
            .execute()
        )
        logger.info(f"Created conversation for user {user_id}: {title}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating conversation for user {user_id}: {e}", exc_info=True)
        return None


async def get_conversations(user_id: str, limit: int = 50, offset: int = 0):
    """Get user's conversations"""
    try:
        response = (
            supabase.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_deleted", False)
            .order("updated_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        logger.debug(f"Fetched {len(response.data)} conversations for user {user_id}")
        return response.data
    except Exception as e:
        logger.error(f"Error fetching conversations for user {user_id}: {e}", exc_info=True)
        return []


async def get_conversation(conversation_id: int, user_id: str = None):
    """Get a specific conversation"""
    try:
        query = supabase.table("conversations").select("*").eq("id", conversation_id)
        if user_id:
            query = query.eq("user_id", user_id)
        response = query.execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {e}", exc_info=True)
        return None


async def update_conversation(conversation_id: int, **kwargs):
    """Update conversation"""
    try:
        response = (
            supabase.table("conversations")
            .update(kwargs)
            .eq("id", conversation_id)
            .execute()
        )
        logger.debug(f"Updated conversation {conversation_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating conversation {conversation_id}: {e}", exc_info=True)
        return None


async def delete_conversation(conversation_id: int):
    """Soft delete conversation"""
    try:
        supabase.table("conversations").update({"is_deleted": True}).eq(
            "id", conversation_id
        ).execute()
        logger.info(f"Deleted conversation {conversation_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {e}", exc_info=True)
        return False


# Message operations
async def create_message(
    conversation_id: int,
    user_id: str,
    role: str,
    content: str,
    model_used: str = None,
    tokens_used: int = None,
):
    """Create a new message"""
    try:
        response = (
            supabase.table("messages")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                    "model_used": model_used,
                    "tokens_used": tokens_used,
                }
            )
            .execute()
        )
        logger.debug(f"Created {role} message in conversation {conversation_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(
            f"Error creating message in conversation {conversation_id}: {e}",
            exc_info=True
        )
        return None


async def get_messages(conversation_id: int, limit: int = 100, offset: int = 0):
    """Get messages from a conversation"""
    try:
        response = (
            supabase.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .range(offset, offset + limit - 1)
            .execute()
        )
        logger.debug(f"Fetched {len(response.data)} messages from conversation {conversation_id}")
        return response.data
    except Exception as e:
        logger.error(
            f"Error fetching messages from conversation {conversation_id}: {e}",
            exc_info=True
        )
        return []


async def get_recent_messages(conversation_id: int, limit: int = 10):
    """Get recent messages for context"""
    try:
        response = (
            supabase.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        logger.debug(f"Fetched {len(response.data)} recent messages from conversation {conversation_id}")
        return response.data
    except Exception as e:
        logger.error(
            f"Error fetching recent messages from conversation {conversation_id}: {e}",
            exc_info=True
        )
        return []


# Memory operations
async def save_memory(user_id: str, content: str, importance: int = 1):
    """Save memory entry"""
    try:
        response = (
            supabase.table("ai_memory")
            .insert({"user_id": user_id, "content": content, "importance": importance})
            .execute()
        )
        logger.info(f"Saved memory for user {user_id} with importance {importance}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error saving memory for user {user_id}: {e}", exc_info=True)
        return None


async def get_user_memory(user_id: str, limit: int = 50):
    """Get user's memory entries"""
    try:
        response = (
            supabase.table("ai_memory")
            .select("*")
            .eq("user_id", user_id)
            .order("importance", desc=True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        logger.debug(f"Fetched {len(response.data)} memory entries for user {user_id}")
        return response.data
    except Exception as e:
        logger.error(f"Error fetching memory for user {user_id}: {e}", exc_info=True)
        return []


# Settings operations
async def get_user_settings(user_id: str):
    """Get user settings"""
    try:
        response = (
            supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching settings for user {user_id}: {e}", exc_info=True)
        return None


async def update_user_settings(user_id: str, **kwargs):
    """Update user settings"""
    try:
        response = (
            supabase.table("user_settings")
            .update(kwargs)
            .eq("user_id", user_id)
            .execute()
        )
        logger.info(f"Updated user settings for {user_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating settings for user {user_id}: {e}", exc_info=True)
        return None
