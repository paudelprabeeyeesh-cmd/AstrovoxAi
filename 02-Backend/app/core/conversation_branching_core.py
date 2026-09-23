"""
Conversation branching and forking.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class ConversationBranch:
    branch_id: str
    parent_branch_id: Optional[str]
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class ConversationBranchManager:
    """Manages conversation branching and forking."""

    def __init__(self):
        self.branches: Dict[str, ConversationBranch] = {}
        self.main_branch: Optional[str] = None

    def create_branch(self, parent_branch_id: Optional[str] = None, fork_message_id: Optional[str] = None) -> str:
        branch_id = str(uuid.uuid4())
        parent = self.branches.get(parent_branch_id) if parent_branch_id else None
        messages = []
        if parent:
            if fork_message_id:
                for msg in parent.messages:
                    messages.append(msg)
                    if id(msg) == fork_message_id:
                        break
            else:
                messages = list(parent.messages)
        branch = ConversationBranch(branch_id=branch_id, parent_branch_id=parent_branch_id, messages=messages)
        self.branches[branch_id] = branch
        if self.main_branch is None:
            self.main_branch = branch_id
        logger.info("Created branch %s from %s", branch_id, parent_branch_id)
        return branch_id

    def add_message(self, branch_id: str, role: str, content: str, metadata: dict = None) -> Message:
        branch = self.branches.get(branch_id)
        if branch is None:
            raise ValueError(f"Branch {branch_id} not found")
        message = Message(role=role, content=content, metadata=metadata or {})
        branch.messages.append(message)
        return message

    def get_branch(self, branch_id: str) -> Optional[ConversationBranch]:
        return self.branches.get(branch_id)

    def list_branches(self) -> List[dict]:
        return [{"branch_id": b.branch_id, "parent": b.parent_branch_id, "message_count": len(b.messages), "created_at": b.created_at.isoformat()} for b in self.branches.values()]

    def merge_branches(self, source_branch_id: str, target_branch_id: str) -> bool:
        source = self.branches.get(source_branch_id)
        target = self.branches.get(target_branch_id)
        if source is None or target is None:
            return False
        target.messages.extend(source.messages)
        return True
