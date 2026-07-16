"""
Conversation Memory - Phase 3.2 Layer 2

Maintains complete chat history including:
- Full message history
- Conversation summaries
- Chat titles
- Timestamps
- Attachments
- Search indexing
- Export support
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import json


class MessageRole(Enum):
    """Roles in a conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMemory:
    """
    Stores complete conversation history with metadata.
    Persists conversations with search capabilities.
    """
    
    def __init__(self):
        self.conversations: Dict[int, Dict[str, Any]] = {}
        self.messages: Dict[int, List[Dict[str, Any]]] = {}
        self.summaries: Dict[int, str] = {}
        self.next_conversation_id = 1
    
    def create_conversation(
        self,
        user_id: int,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Create a new conversation.
        
        Args:
            user_id: User ID
            title: Optional conversation title
            metadata: Additional metadata
        
        Returns:
            Conversation ID
        """
        conversation_id = self.next_conversation_id
        self.next_conversation_id += 1
        
        self.conversations[conversation_id] = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": title or "New Conversation",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "message_count": 0,
            "attachments": [],
        }
        
        self.messages[conversation_id] = []
        
        return conversation_id
    
    def add_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role
            content: Message content
            metadata: Additional metadata
        
        Returns:
            Message ID
        """
        if conversation_id not in self.messages:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        message_id = len(self.messages[conversation_id])
        message = {
            "message_id": message_id,
            "role": role.value,
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        self.messages[conversation_id].append(message)
        
        # Update conversation metadata
        self.conversations[conversation_id]["updated_at"] = datetime.utcnow().isoformat()
        self.conversations[conversation_id]["message_count"] += 1
        
        return message_id
    
    def get_conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get conversation metadata"""
        return self.conversations.get(conversation_id)
    
    def get_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Optional limit on number of messages
            offset: Offset for pagination
        
        Returns:
            List of messages
        """
        if conversation_id not in self.messages:
            return []
        
        messages = self.messages[conversation_id]
        end = offset + limit if limit else None
        
        return messages[offset:end]
    
    def get_user_conversations(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        user_conversations = [
            conv for conv in self.conversations.values()
            if conv["user_id"] == user_id
        ]
        
        # Sort by updated_at (most recent first)
        user_conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return user_conversations[offset:offset + limit]
    
    def update_conversation_title(
        self,
        conversation_id: int,
        title: str,
    ):
        """Update conversation title"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id]["title"] = title
            self.conversations[conversation_id]["updated_at"] = datetime.utcnow().isoformat()
    
    def set_summary(self, conversation_id: int, summary: str):
        """Set conversation summary"""
        self.summaries[conversation_id] = summary
    
    def get_summary(self, conversation_id: int) -> Optional[str]:
        """Get conversation summary"""
        return self.summaries.get(conversation_id)
    
    def add_attachment(
        self,
        conversation_id: int,
        attachment: Dict[str, Any],
    ):
        """Add an attachment to a conversation"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id]["attachments"].append(attachment)
    
    def delete_conversation(self, conversation_id: int):
        """Delete a conversation"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
        if conversation_id in self.messages:
            del self.messages[conversation_id]
        if conversation_id in self.summaries:
            del self.summaries[conversation_id]
    
    def search_conversations(
        self,
        user_id: int,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by content.
        
        Args:
            user_id: User ID
            query: Search query
            limit: Result limit
        
        Returns:
            List of matching conversations
        """
        query_lower = query.lower()
        results = []
        
        for conv in self.conversations.values():
            if conv["user_id"] != user_id:
                continue
            
            # Search in title
            if query_lower in conv["title"].lower():
                results.append(conv)
                continue
            
            # Search in messages
            if conv["conversation_id"] in self.messages:
                for msg in self.messages[conv["conversation_id"]]:
                    if query_lower in msg["content"].lower():
                        results.append(conv)
                        break
        
        return results[:limit]
    
    def export_conversation(
        self,
        conversation_id: int,
        format: str = "json",
    ) -> str:
        """
Export a conversation.
        
        Args:
            conversation_id: Conversation ID
            format: Export format (json, markdown, txt)
        
        Returns:
            Exported conversation as string
        """
        conversation = self.get_conversation(conversation_id)
        messages = self.get_messages(conversation_id)
        
        if not conversation:
            return ""
        
        if format == "json":
            return json.dumps({
                "conversation": conversation,
                "messages": messages,
                "summary": self.get_summary(conversation_id),
            }, indent=2)
        
        elif format == "markdown":
            lines = [
                f"# {conversation['title']}",
                f"Created: {conversation['created_at']}",
                "",
                "## Messages",
                "",
            ]
            
            for msg in messages:
                lines.append(f"### {msg['role'].capitalize()}")
                lines.append(msg['content'])
                lines.append("")
            
            return "\n".join(lines)
        
        elif format == "txt":
            lines = [
                f"Conversation: {conversation['title']}",
                f"Created: {conversation['created_at']}",
                "",
                "Messages:",
                "",
            ]
            
            for msg in messages:
                lines.append(f"[{msg['role']}]: {msg['content']}")
            
            return "\n".join(lines)
        
        return ""
    
    def get_conversation_stats(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get statistics for a conversation"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        
        messages = self.get_messages(conversation_id)
        
        user_messages = [m for m in messages if m["role"] == MessageRole.USER.value]
        assistant_messages = [m for m in messages if m["role"] == MessageRole.ASSISTANT.value]
        
        total_chars = sum(len(m["content"]) for m in messages)
        
        return {
            "conversation_id": conversation_id,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "total_characters": total_chars,
            "average_message_length": total_chars / len(messages) if messages else 0,
            "has_attachments": len(conversation.get("attachments", [])) > 0,
            "has_summary": conversation_id in self.summaries,
        }
