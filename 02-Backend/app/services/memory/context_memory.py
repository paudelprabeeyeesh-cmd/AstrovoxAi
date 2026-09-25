"""
Context Memory - Phase 3.2 Layer 1

Short-term memory for the current conversation context.
Stores only the current session, recent messages, active task, and temporary variables.
Automatically cleared when no longer needed.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum


class ContextType(Enum):
    """Types of context information"""
    MESSAGE = "message"
    TASK = "task"
    VARIABLE = "variable"
    METADATA = "metadata"


class ContextMemory:
    """
    Short-term context memory for the current conversation.
    Automatically expires after a period of inactivity.
    """
    
    def __init__(self, ttl_minutes: int = 30):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.context: Dict[str, Dict[str, Any]] = {}
        self.last_accessed: Dict[str, datetime] = {}
    
    def add_context(
        self,
        key: str,
        value: Any,
        context_type: ContextType,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Add context information.
        
        Args:
            key: Unique key for the context
            value: Context value
            context_type: Type of context
            metadata: Additional metadata
        """
        self.context[key] = {
            "value": value,
            "type": context_type.value,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        self.last_accessed[key] = datetime.utcnow()
    
    def get_context(self, key: str) -> Optional[Any]:
        """Get context by key"""
        if key not in self.context:
            return None
        
        # Check if expired
        if self._is_expired(key):
            self.remove_context(key)
            return None
        
        self.last_accessed[key] = datetime.utcnow()
        return self.context[key]["value"]
    
    def get_all_context(self, context_type: Optional[ContextType] = None) -> Dict[str, Any]:
        """Get all context, optionally filtered by type"""
        self._cleanup_expired()
        
        result = {}
        for key, data in self.context.items():
            if context_type is None or data["type"] == context_type.value:
                result[key] = data["value"]
        
        return result
    
    def remove_context(self, key: str):
        """Remove context by key"""
        if key in self.context:
            del self.context[key]
        if key in self.last_accessed:
            del self.last_accessed[key]
    
    def clear_all(self):
        """Clear all context"""
        self.context.clear()
        self.last_accessed.clear()
    
    def _is_expired(self, key: str) -> bool:
        """Check if context has expired"""
        if key not in self.last_accessed:
            return True
        
        last_access = self.last_accessed[key]
        return datetime.utcnow() - last_access > self.ttl
    
    def _cleanup_expired(self):
        """Remove all expired context"""
        expired_keys = [
            key for key in self.context.keys()
            if self._is_expired(key)
        ]
        for key in expired_keys:
            self.remove_context(key)
    
    def add_message(self, role: str, content: str, message_id: str):
        """Add a message to context"""
        self.add_context(
            key=f"message_{message_id}",
            value={"role": role, "content": content},
            context_type=ContextType.MESSAGE,
            metadata={"message_id": message_id},
        )
    
    def set_active_task(self, task: str, task_id: str):
        """Set the active task"""
        self.add_context(
            key="active_task",
            value={"task": task, "task_id": task_id},
            context_type=ContextType.TASK,
            metadata={"task_id": task_id},
        )
    
    def get_active_task(self) -> Optional[Dict[str, Any]]:
        """Get the active task"""
        return self.get_context("active_task")
    
    def set_variable(self, name: str, value: Any):
        """Set a temporary variable"""
        self.add_context(
            key=f"var_{name}",
            value=value,
            context_type=ContextType.VARIABLE,
            metadata={"variable_name": name},
        )
    
    def get_variable(self, name: str) -> Optional[Any]:
        """Get a temporary variable"""
        return self.get_context(f"var_{name}")
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from context"""
        messages = []
        for key, data in self.context.items():
            if data["type"] == ContextType.MESSAGE.value:
                messages.append({
                    "message_id": data["metadata"].get("message_id"),
                    "role": data["value"]["role"],
                    "content": data["value"]["content"],
                    "created_at": data["created_at"],
                })
        
        # Sort by creation time and limit
        messages.sort(key=lambda x: x["created_at"], reverse=True)
        return messages[:limit]
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of current context"""
        self._cleanup_expired()
        
        summary = {
            "total_items": len(self.context),
            "by_type": {},
            "active_task": self.get_active_task(),
            "recent_messages_count": len(self.get_recent_messages()),
        }
        
        # Count by type
        for data in self.context.values():
            context_type = data["type"]
            if context_type not in summary["by_type"]:
                summary["by_type"][context_type] = 0
            summary["by_type"][context_type] += 1
        
        return summary
