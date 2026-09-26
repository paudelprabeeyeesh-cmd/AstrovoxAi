"""Enterprise collaboration package initialization."""
from .chat import CollaborationChat, ChatMessage
from .documents import DocumentCollaboration, DocumentVersion
from .meetings import MeetingManager, MeetingRecord

__all__ = [
    "CollaborationChat",
    "ChatMessage",
    "DocumentCollaboration",
    "DocumentVersion",
    "MeetingManager",
    "MeetingRecord",
]
