"""
Conversation history management with persistence and retrieval.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))


@dataclass
class Conversation:
    conversation_id: str
    title: str
    messages: List[ConversationMessage] = field(default_factory=list)
    user_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    pinned: bool = False
    archived: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"conversation_id": self.conversation_id, "title": self.title, "user_id": self.user_id, "message_count": len(self.messages), "created_at": self.created_at, "updated_at": self.updated_at, "pinned": self.pinned, "archived": self.archived}

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> ConversationMessage:
        message = ConversationMessage(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)
        self.updated_at = time.time()
        return message

    def get_last_messages(self, n: int = 10) -> List[ConversationMessage]:
        return self.messages[-n:]

    def search_messages(self, query: str, top_k: int = 5) -> List[ConversationMessage]:
        query_lower = query.lower()
        scored = []
        for msg in self.messages:
            if query_lower in msg.content.lower():
                scored.append((msg.content.lower().count(query_lower), msg))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [msg for _, msg in scored[:top_k]]


class ConversationHistoryManager:
    """Manage conversation history with persistence."""

    def __init__(self, storage_path: str = "conversation_history.json"):
        self.storage_path = storage_path
        self.conversations: Dict[str, Conversation] = {}
        self.user_conversations: Dict[str, List[str]] = defaultdict(list)
        self._load_from_disk()

    def create_conversation(self, user_id: str, title: str = "New Conversation", metadata: Optional[Dict[str, Any]] = None) -> Conversation:
        conv_id = str(__import__("uuid").uuid4())
        conv = Conversation(conversation_id=conv_id, title=title, user_id=user_id, metadata=metadata or {})
        self.conversations[conv_id] = conv
        self.user_conversations[user_id].append(conv_id)
        self._save_to_disk()
        return conv

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self.conversations.get(conversation_id)

    def get_user_conversations(self, user_id: str) -> List[Conversation]:
        return [self.conversations[cid] for cid in self.user_conversations.get(user_id, []) if cid in self.conversations]

    def add_message(self, conversation_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[ConversationMessage]:
        conv = self.conversations.get(conversation_id)
        if conv:
            msg = conv.add_message(role, content, metadata)
            self._save_to_disk()
            return msg
        return None

    def search_user_conversations(self, user_id: str, query: str, top_k: int = 10) -> List[ConversationMessage]:
        results = []
        for conv in self.get_user_conversations(user_id):
            results.extend(conv.search_messages(query, top_k=top_k))
        results.sort(key=lambda m: m.timestamp, reverse=True)
        return results[:top_k]

    def pin_conversation(self, conversation_id: str) -> bool:
        conv = self.conversations.get(conversation_id)
        if conv:
            conv.pinned = True
            self._save_to_disk()
            return True
        return False

    def archive_conversation(self, conversation_id: str) -> bool:
        conv = self.conversations.get(conversation_id)
        if conv:
            conv.archived = True
            self._save_to_disk()
            return True
        return False

    def delete_conversation(self, conversation_id: str) -> bool:
        conv = self.conversations.pop(conversation_id, None)
        if conv:
            if conv.user_id in self.user_conversations:
                self.user_conversations[conv.user_id].remove(conversation_id)
            self._save_to_disk()
            return True
        return False

    def _save_to_disk(self):
        try:
            data = {}
            for cid, conv in self.conversations.items():
                data[cid] = {"conversation_id": conv.conversation_id, "title": conv.title, "user_id": conv.user_id, "messages": [{"role": m.role, "content": m.content, "timestamp": m.timestamp, "metadata": m.metadata} for m in conv.messages], "created_at": conv.created_at, "updated_at": conv.updated_at, "pinned": conv.pinned, "archived": conv.archived}
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save conversation history: {e}")

    def _load_from_disk(self):
        try:
            if not os.path.exists(self.storage_path):
                return
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            for cid, conv_data in data.items():
                conv = Conversation(conversation_id=conv_data["conversation_id"], title=conv_data["title"], user_id=conv_data["user_id"], created_at=conv_data["created_at"], updated_at=conv_data["updated_at"], pinned=conv_data.get("pinned", False), archived=conv_data.get("archived", False))
                for msg_data in conv_data.get("messages", []):
                    msg = ConversationMessage(role=msg_data["role"], content=msg_data["content"], timestamp=msg_data.get("timestamp", time.time()), metadata=msg_data.get("metadata", {}))
                    conv.messages.append(msg)
                self.conversations[cid] = conv
                self.user_conversations[conv.user_id].append(cid)
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")


conversation_history = ConversationHistoryManager()
