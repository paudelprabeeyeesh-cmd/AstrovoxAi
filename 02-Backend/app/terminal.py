"""Terminal console endpoints.

Only the operations with no existing backend equivalent live here:
  POST /api/terminal/inject  — persist a memory entry (reuses ai_memory table)
  POST /api/terminal/purge   — delete all of the user's memory entries
  GET  /api/terminal/usage   — today's AI usage count + configured limit
Everything else the terminal needs is served by /api/status, /api/stats,
/api/memory and /health.
"""

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from .auth_utils import get_user_id_from_token
from .database import save_memory, get_user_memory
from .supabase_client import get_supabase
from .usage import DailyUsageTracker

router = APIRouter(prefix="/api/terminal", tags=["terminal"])

MAX_CONTENT_LENGTH = 500


class InjectRequest(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)


@router.post("/inject")
async def inject_memory(request: InjectRequest, authorization: str = Header(None)):
    """Persist a memory entry on behalf of the authenticated terminal user."""
    user_id = get_user_id_from_token(authorization)

    content = request.content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Injection content cannot be empty",
        )

    entry = await save_memory(user_id, content, importance=1)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist memory entry",
        )
    return {"status": "OK", "memory": entry}


@router.post("/purge")
async def purge_memory(authorization: str = Header(None)):
    """Delete ALL memory entries for the authenticated user (destructive)."""
    user_id = get_user_id_from_token(authorization)

    try:
        supabase = get_supabase()
        response = (
            supabase.table("ai_memory")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        deleted = len(response.data) if response.data else 0
        return {"status": "OK", "deleted": deleted}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge memory: {str(exc)}",
        ) from exc


@router.get("/usage")
async def terminal_usage(authorization: str = Header(None)):
    """Return today's AI request count and the configured daily limit."""
    user_id = get_user_id_from_token(authorization)

    tracker = DailyUsageTracker()
    used = await tracker.get_count(user_id)
    return {
        "status": "OK",
        "used": used,
        "limit": tracker.limit,
        "resets": "daily (UTC)",
    }
