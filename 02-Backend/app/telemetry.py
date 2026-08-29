"""Telemetry and event tracking for AstrovoxAi backend."""

import os
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from .auth_utils import get_user_id_from_token
from .logging_config import logger
from .supabase_client import get_supabase

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
supabase = get_supabase()


class TelemetryEvent(BaseModel):
    """Telemetry event schema."""
    
    event_name: str
    category: Optional[str] = "general"
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class PageViewEvent(BaseModel):
    """Page view tracking."""
    
    page: str
    referrer: Optional[str] = None


class ErrorEvent(BaseModel):
    """Error tracking."""
    
    error_name: str
    error_message: str
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class UserActionEvent(BaseModel):
    """User action tracking."""
    
    action: str
    category: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/event")
async def track_event(
    event: TelemetryEvent,
    authorization: str = Header(None)
) -> Dict[str, Any]:
    """Track a custom telemetry event."""
    user_id = get_user_id_from_token(authorization)
    
    try:
        timestamp = event.timestamp or datetime.now(timezone.utc).isoformat()
        
        # Insert event into telemetry table
        response = supabase.table("telemetry_events").insert({
            "user_id": user_id,
            "event_name": event.event_name,
            "category": event.category,
            "metadata": json.dumps(event.metadata or {}),
            "timestamp": timestamp,
        }).execute()
        
        logger.info(
            f"Telemetry event tracked: {event.event_name}",
            extra={
                "user_id": user_id,
                "category": event.category,
                "timestamp": timestamp
            }
        )
        
        return {
            "status": "OK",
            "event_id": response.data[0].get("id") if response.data else None,
            "message": "Event tracked successfully"
        }
    except Exception as e:
        logger.error(f"Failed to track telemetry event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track event: {str(e)}"
        )


@router.post("/page-view")
async def track_page_view(
    event: PageViewEvent,
    authorization: str = Header(None)
) -> Dict[str, Any]:
    """Track a page view event."""
    user_id = get_user_id_from_token(authorization)
    
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        response = supabase.table("telemetry_events").insert({
            "user_id": user_id,
            "event_name": "page_view",
            "category": "navigation",
            "metadata": json.dumps({
                "page": event.page,
                "referrer": event.referrer
            }),
            "timestamp": timestamp,
        }).execute()
        
        logger.info(
            f"Page view tracked: {event.page}",
            extra={"user_id": user_id, "page": event.page}
        )
        
        return {
            "status": "OK",
            "event_id": response.data[0].get("id") if response.data else None,
            "message": "Page view tracked"
        }
    except Exception as e:
        logger.error(f"Failed to track page view: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track page view: {str(e)}"
        )


@router.post("/error")
async def track_error(
    event: ErrorEvent,
    authorization: str = Header(None)
) -> Dict[str, Any]:
    """Track an error event."""
    user_id = get_user_id_from_token(authorization)
    
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        response = supabase.table("telemetry_events").insert({
            "user_id": user_id,
            "event_name": "error",
            "category": "error",
            "metadata": json.dumps({
                "error_name": event.error_name,
                "error_message": event.error_message,
                "stack_trace": event.stack_trace,
                "context": event.context
            }),
            "timestamp": timestamp,
        }).execute()
        
        logger.error(
            f"Error tracked: {event.error_name}: {event.error_message}",
            extra={"user_id": user_id, "stack_trace": event.stack_trace}
        )
        
        return {
            "status": "OK",
            "event_id": response.data[0].get("id") if response.data else None,
            "message": "Error tracked"
        }
    except Exception as e:
        logger.error(f"Failed to track error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track error: {str(e)}"
        )


@router.post("/user-action")
async def track_user_action(
    event: UserActionEvent,
    authorization: str = Header(None)
) -> Dict[str, Any]:
    """Track a user action event."""
    user_id = get_user_id_from_token(authorization)
    
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        response = supabase.table("telemetry_events").insert({
            "user_id": user_id,
            "event_name": event.action,
            "category": event.category,
            "metadata": json.dumps(event.metadata or {}),
            "timestamp": timestamp,
        }).execute()
        
        logger.info(
            f"User action tracked: {event.action}",
            extra={
                "user_id": user_id,
                "category": event.category,
                "action": event.action
            }
        )
        
        return {
            "status": "OK",
            "event_id": response.data[0].get("id") if response.data else None,
            "message": "User action tracked"
        }
    except Exception as e:
        logger.error(f"Failed to track user action: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track user action: {str(e)}"
        )


@router.get("/stats")
async def get_telemetry_stats(
    authorization: str = Header(None),
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get telemetry statistics for the current user."""
    user_id = get_user_id_from_token(authorization)
    
    try:
        response = supabase.table("telemetry_events").select(
            "id, event_name, category, timestamp"
        ).eq("user_id", user_id).order(
            "timestamp", desc=True
        ).range(offset, offset + limit - 1).execute()
        
        events = response.data or []
        
        # Calculate statistics
        event_counts = {}
        category_counts = {}
        
        for event in events:
            event_name = event.get("event_name", "unknown")
            category = event.get("category", "unknown")
            
            event_counts[event_name] = event_counts.get(event_name, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "status": "OK",
            "user_id": user_id,
            "total_events": len(events),
            "event_counts": event_counts,
            "category_counts": category_counts,
            "recent_events": events,
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Failed to get telemetry stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )
