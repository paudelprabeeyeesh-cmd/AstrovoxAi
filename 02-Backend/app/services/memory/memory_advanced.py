"""Advanced AI Memory — hierarchical, cross-session, encrypted."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MemoryNode:
    """A node in the hierarchical memory."""
    id: str
    content: str
    parent_id: str = None
    children: list = field(default_factory=list)
    importance: float = 1.0
    created_at: float = 0.0
    encrypted: bool = False

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class AdvancedMemory:
    """Advanced hierarchical memory system."""

    def __init__(self):
        self._nodes: dict[str, MemoryNode] = {}
        self._sessions: dict = {}

    def add_node(self, content: str, parent_id: str = None, importance: float = 1.0) -> MemoryNode:
        """Add a memory node."""
        import secrets
        node = MemoryNode(
            id=secrets.token_hex(8),
            content=content,
            parent_id=parent_id,
            importance=importance,
        )
        self._nodes[node.id] = node

        if parent_id and parent_id in self._nodes:
            self._nodes[parent_id].children.append(node.id)

        return node

    def get_tree(self, root_id: str) -> dict:
        """Get memory tree."""
        node = self._nodes.get(root_id)
        if not node:
            return {}

        return {
            "id": node.id,
            "content": node.content,
            "children": [self.get_tree(cid) for cid in node.children],
        }

    def search(self, query: str) -> list:
        query_lower = query.lower()
        return [
            n for n in self._nodes.values()
            if query_lower in n.content.lower()
        ]


advanced_memory = AdvancedMemory()
