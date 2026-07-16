"""
Episodic Memory - Phase 3.2 Layer 4

Stores important events with timestamps and context:
- Started Astrovox project
- Finished deployment
- Created first AI agent
- Published first release
- Completed milestone

These memories include timestamps, context, and emotional significance.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """Types of episodic events"""
    MILESTONE = "milestone"
    ACHIEVEMENT = "achievement"
    PROJECT_START = "project_start"
    PROJECT_END = "project_end"
    IMPORTANT_DECISION = "important_decision"
    LEARNING_EVENT = "learning_event"
    SIGNIFICANT_CHANGE = "significant_change"


class EpisodicMemory:
    """
    Stores important events and milestones with temporal context.
    Helps the AI remember significant moments in the user's journey.
    """
    
    def __init__(self):
        self.events: Dict[str, Dict[str, Any]] = {}
        self.next_event_id = 1
    
    def add_event(
        self,
        user_id: int,
        event_type: EventType,
        title: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        significance: float = 0.5,
        related_project: Optional[str] = None,
    ) -> str:
        """
        Add an episodic event.
        
        Args:
            user_id: User ID
            event_type: Type of event
            title: Event title
            description: Event description
            context: Additional context
            significance: Significance score (0.0 to 1.0)
            related_project: Related project/workspace
        
        Returns:
            Event ID
        """
        event_id = f"event_{self.next_event_id}"
        self.next_event_id += 1
        
        self.events[event_id] = {
            "event_id": event_id,
            "user_id": user_id,
            "event_type": event_type.value,
            "title": title,
            "description": description,
            "context": context or {},
            "significance": significance,
            "related_project": related_project,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return event_id
    
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get an event by ID"""
        return self.events.get(event_id)
    
    def get_user_events(
        self,
        user_id: int,
        event_type: Optional[EventType] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get events for a user, optionally filtered by type.
        
        Args:
            user_id: User ID
            event_type: Optional event type filter
            limit: Result limit
        
        Returns:
            List of events
        """
        user_events = [
            event for event in self.events.values()
            if event["user_id"] == user_id
        ]
        
        if event_type:
            user_events = [
                event for event in user_events
                if event["event_type"] == event_type.value
            ]
        
        # Sort by created_at (most recent first)
        user_events.sort(key=lambda x: x["created_at"], reverse=True)
        
        return user_events[:limit]
    
    def get_project_events(
        self,
        user_id: int,
        project_name: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get events related to a specific project"""
        project_events = [
            event for event in self.events.values()
            if event["user_id"] == user_id and event["related_project"] == project_name
        ]
        
        project_events.sort(key=lambda x: x["created_at"], reverse=True)
        
        return project_events[:limit]
    
    def get_significant_events(
        self,
        user_id: int,
        threshold: float = 0.7,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get events above a significance threshold"""
        significant_events = [
            event for event in self.events.values()
            if event["user_id"] == user_id and event["significance"] >= threshold
        ]
        
        significant_events.sort(key=lambda x: x["significance"], reverse=True)
        
        return significant_events[:limit]
    
    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        significance: Optional[float] = None,
    ):
        """Update an event"""
        if event_id in self.events:
            if title is not None:
                self.events[event_id]["title"] = title
            if description is not None:
                self.events[event_id]["description"] = description
            if significance is not None:
                self.events[event_id]["significance"] = significance
    
    def delete_event(self, event_id: str):
        """Delete an event"""
        if event_id in self.events:
            del self.events[event_id]
    
    def search_events(
        self,
        user_id: int,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search events by content"""
        query_lower = query.lower()
        results = []
        
        for event in self.events.values():
            if event["user_id"] != user_id:
                continue
            
            if query_lower in event["title"].lower() or query_lower in event["description"].lower():
                results.append(event)
        
        return results[:limit]
    
    def get_timeline(
        self,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get a timeline of events within a date range.
        
        Args:
            user_id: User ID
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)
        
        Returns:
            Chronological list of events
        """
        user_events = self.get_user_events(user_id, limit=None)
        
        # Filter by date range
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            user_events = [
                event for event in user_events
                if datetime.fromisoformat(event["created_at"]) >= start_dt
            ]
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            user_events = [
                event for event in user_events
                if datetime.fromisoformat(event["created_at"]) <= end_dt
            ]
        
        # Sort chronologically (oldest first)
        user_events.sort(key=lambda x: x["created_at"])
        
        return user_events
    
    def get_summary(self, user_id: int) -> Dict[str, Any]:
        """Get a summary of episodic memory for a user"""
        user_events = self.get_user_events(user_id, limit=None)
        
        by_type = {}
        for event in user_events:
            event_type = event["event_type"]
            if event_type not in by_type:
                by_type[event_type] = 0
            by_type[event_type] += 1
        
        significant_count = sum(
            1 for event in user_events
            if event["significance"] >= 0.7
        )
        
        # Get most recent event
        most_recent = user_events[0] if user_events else None
        
        return {
            "total_events": len(user_events),
            "by_type": by_type,
            "significant_events": significant_count,
            "most_recent_event": most_recent,
            "projects_with_events": len(set(
                event["related_project"] for event in user_events
                if event["related_project"]
            )),
        }
