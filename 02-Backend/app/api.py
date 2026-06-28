from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, status

from .auth_utils import get_user_id_from_token
from .database import (
    get_user_profile,
    get_user_memory,
    get_conversations,
    save_memory,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/status")
async def api_status():
    """API status endpoint"""
    return {
        "status": "OK",
        "service": "astravox-ai-api",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/me")
async def get_me(authorization: str = Header(None)):
    """Get current user profile"""
    user_id = get_user_id_from_token(authorization)

    try:
        profile = await get_user_profile(user_id)
        return {"status": "OK", "user": {"id": user_id, "profile": profile}}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user profile: {str(e)}",
        )


@router.get("/stats")
async def get_user_stats(authorization: str = Header(None)):
    """Get user statistics"""
    user_id = get_user_id_from_token(authorization)

    try:
        profile = await get_user_profile(user_id)
        conversations = await get_conversations(user_id, limit=1000)
        memory = await get_user_memory(user_id, limit=1000)

        # Calculate stats
        total_conversations = len(conversations)
        total_memory_entries = len(memory)

        return {
            "status": "OK",
            "stats": {
                "total_conversations": total_conversations,
                "total_memory_entries": total_memory_entries,
                "user_tier": profile.get("tier", "free") if profile else "free",
                "created_at": profile.get("created_at") if profile else None,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stats: {str(e)}",
        )


@router.get("/memory")
async def get_memory(authorization: str = Header(None), limit: int = 50):
    """Get user memory"""
    user_id = get_user_id_from_token(authorization)

    try:
        memory = await get_user_memory(user_id, limit)
        return {"status": "OK", "memory": memory, "count": len(memory)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch memory: {str(e)}",
        )


@router.post("/memory")
async def save_user_memory(
    content: str, importance: int = 1, authorization: str = Header(None)
):
    """Save memory entry"""
    user_id = get_user_id_from_token(authorization)

    try:
        memory = await save_memory(user_id, content, importance)
        return {"status": "OK", "memory": memory}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save memory: {str(e)}",
        )
