"""
Knowledge Workspace Isolation - Phase 5.10

Knowledge must not leak across workspaces.

Example:
- School workspace contains notes, books, and assignments.
- Trading workspace contains strategies, journals, and market research.
- Work workspace contains code, APIs, and product documents.

Each workspace should have its own search index and permission boundary.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class WorkspaceType(Enum):
    """Types of workspaces"""
    SCHOOL = "school"
    TRADING = "trading"
    WORK = "work"
    PERSONAL = "personal"
    RESEARCH = "research"
    GENERAL = "general"


class KnowledgeWorkspace:
    """
    Isolated knowledge workspace for a specific context.
    Prevents information leakage and maintains separate search indices.
    """
    
    def __init__(
        self,
        workspace_id: str,
        name: str,
        workspace_type: WorkspaceType,
        owner_id: int,
        description: Optional[str] = None,
    ):
        self.workspace_id = workspace_id
        self.name = name
        self.workspace_type = workspace_type
        self.owner_id = owner_id
        self.description = description or ""
        
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
        
        # Knowledge items in this workspace
        self.knowledge_items: Dict[str, Dict[str, Any]] = {}
        self.next_item_id = 1
        
        # Search index for this workspace
        self.search_index: Dict[str, List[str]] = {}  # term -> item_ids
        
        # Workspace-specific settings
        self.settings = {
            "auto_index": True,
            "share_with_team": False,
            "allow_cross_workspace_search": False,
        }
    
    def add_knowledge_item(
        self,
        content: str,
        item_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a knowledge item to the workspace.
        
        Args:
            content: Content of the knowledge item
            item_type: Type of item (note, document, etc.)
            metadata: Additional metadata
        
        Returns:
            Item ID
        """
        item_id = f"item_{self.next_item_id}"
        self.next_item_id += 1
        
        item = {
            "item_id": item_id,
            "content": content,
            "item_type": item_type,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "workspace_id": self.workspace_id,
        }
        
        self.knowledge_items[item_id] = item
        
        # Auto-index if enabled
        if self.settings["auto_index"]:
            self._index_item(item_id, content)
        
        self.updated_at = datetime.utcnow().isoformat()
        
        return item_id
    
    def _index_item(self, item_id: str, content: str):
        """Index a knowledge item for search"""
        # Simple word-based indexing
        words = content.lower().split()
        
        for word in words:
            if word not in self.search_index:
                self.search_index[word] = []
            
            if item_id not in self.search_index[word]:
                self.search_index[word].append(item_id)
    
    def search_workspace(
        self,
        query: str,
        item_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search within this workspace only.
        
        Args:
            query: Search query
            item_type: Optional filter by item type
            limit: Maximum results
        
        Returns:
            Matching knowledge items
        """
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # Score items based on query matches
        scored_items = {}
        
        for word in query_words:
            if word in self.search_index:
                for item_id in self.search_index[word]:
                    if item_id not in scored_items:
                        scored_items[item_id] = 0
                    scored_items[item_id] += 1
        
        # Convert to list and sort by score
        results = []
        for item_id, score in sorted(scored_items.items(), key=lambda x: x[1], reverse=True):
            item = self.knowledge_items.get(item_id)
            if item:
                # Filter by type if specified
                if item_type and item.get("item_type") != item_type:
                    continue
                
                results.append({
                    **item,
                    "relevance_score": score,
                })
        
        return results[:limit]
    
    def get_knowledge_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific knowledge item"""
        return self.knowledge_items.get(item_id)
    
    def update_knowledge_item(
        self,
        item_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update a knowledge item"""
        item = self.knowledge_items.get(item_id)
        if not item:
            return False
        
        # Re-index if content changed
        if content and content != item["content"]:
            # Remove from old index
            self._unindex_item(item_id, item["content"])
            
            # Update content
            item["content"] = content
            
            # Re-index
            if self.settings["auto_index"]:
                self._index_item(item_id, content)
        
        # Update metadata
        if metadata:
            item["metadata"].update(metadata)
        
        item["updated_at"] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
        
        return True
    
    def _unindex_item(self, item_id: str, content: str):
        """Remove item from search index"""
        words = content.lower().split()
        
        for word in words:
            if word in self.search_index and item_id in self.search_index[word]:
                self.search_index[word].remove(item_id)
                
                # Clean up empty entries
                if not self.search_index[word]:
                    del self.search_index[word]
    
    def delete_knowledge_item(self, item_id: str) -> bool:
        """Delete a knowledge item"""
        item = self.knowledge_items.get(item_id)
        if not item:
            return False
        
        # Remove from index
        self._unindex_item(item_id, item["content"])
        
        # Remove from items
        del self.knowledge_items[item_id]
        
        self.updated_at = datetime.utcnow().isoformat()
        
        return True
    
    def get_all_items(self, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all items in the workspace"""
        items = list(self.knowledge_items.values())
        
        if item_type:
            items = [item for item in items if item.get("item_type") == item_type]
        
        return items
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get workspace statistics"""
        by_type = {}
        for item in self.knowledge_items.values():
            item_type = item.get("item_type", "unknown")
            by_type[item_type] = by_type.get(item_type, 0) + 1
        
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "workspace_type": self.workspace_type.value,
            "total_items": len(self.knowledge_items),
            "by_type": by_type,
            "indexed_terms": len(self.search_index),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    def update_settings(self, settings: Dict[str, Any]):
        """Update workspace settings"""
        self.settings.update(settings)
        self.updated_at = datetime.utcnow().isoformat()


class WorkspaceIsolationManager:
    """
    Manages multiple knowledge workspaces with strict isolation.
    Ensures knowledge does not leak between workspaces.
    """
    
    def __init__(self):
        self.workspaces: Dict[str, KnowledgeWorkspace] = {}
        self.next_workspace_id = 1
    
    def create_workspace(
        self,
        name: str,
        workspace_type: WorkspaceType,
        owner_id: int,
        description: Optional[str] = None,
    ) -> KnowledgeWorkspace:
        """
        Create a new isolated workspace.
        
        Args:
            name: Name of the workspace
            workspace_type: Type of workspace
            owner_id: Owner user ID
            description: Optional description
        
        Returns:
            Created workspace
        """
        workspace_id = f"workspace_{self.next_workspace_id}"
        self.next_workspace_id += 1
        
        workspace = KnowledgeWorkspace(
            workspace_id=workspace_id,
            name=name,
            workspace_type=workspace_type,
            owner_id=owner_id,
            description=description,
        )
        
        self.workspaces[workspace_id] = workspace
        return workspace
    
    def get_workspace(self, workspace_id: str) -> Optional[KnowledgeWorkspace]:
        """Get a workspace by ID"""
        return self.workspaces.get(workspace_id)
    
    def get_user_workspaces(self, user_id: int) -> List[KnowledgeWorkspace]:
        """Get all workspaces for a user"""
        return [
            workspace for workspace in self.workspaces.values()
            if workspace.owner_id == user_id
        ]
    
    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace"""
        if workspace_id in self.workspaces:
            del self.workspaces[workspace_id]
            return True
        return False
    
    def search_within_workspace(
        self,
        workspace_id: str,
        query: str,
        item_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search within a specific workspace.
        Ensures results only come from that workspace.
        
        Args:
            workspace_id: ID of workspace to search
            query: Search query
            item_type: Optional filter by item type
            limit: Maximum results
        
        Returns:
            Results from the specified workspace only
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return []
        
        return workspace.search_workspace(query, item_type, limit)
    
    def cross_workspace_search(
        self,
        workspace_ids: List[str],
        query: str,
        item_type: Optional[str] = None,
        limit_per_workspace: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across multiple workspaces (if allowed).
        
        Args:
            workspace_ids: List of workspace IDs to search
            query: Search query
            item_type: Optional filter by item type
            limit_per_workspace: Maximum results per workspace
        
        Returns:
            Dictionary mapping workspace IDs to results
        """
        results = {}
        
        for workspace_id in workspace_ids:
            workspace = self.get_workspace(workspace_id)
            
            # Check if cross-workspace search is allowed
            if not workspace or not workspace.settings.get("allow_cross_workspace_search", False):
                continue
            
            workspace_results = workspace.search_workspace(query, item_type, limit_per_workspace)
            results[workspace_id] = workspace_results
        
        return results
    
    def transfer_item(
        self,
        item_id: str,
        from_workspace_id: str,
        to_workspace_id: str,
    ) -> bool:
        """
        Transfer a knowledge item between workspaces.
        
        Args:
            item_id: ID of item to transfer
            from_workspace_id: Source workspace ID
            to_workspace_id: Destination workspace ID
        
        Returns:
            Success status
        """
        from_workspace = self.get_workspace(from_workspace_id)
        to_workspace = self.get_workspace(to_workspace_id)
        
        if not from_workspace or not to_workspace:
            return False
        
        item = from_workspace.get_knowledge_item(item_id)
        if not item:
            return False
        
        # Add to destination workspace
        to_workspace.add_knowledge_item(
            content=item["content"],
            item_type=item["item_type"],
            metadata=item["metadata"],
        )
        
        # Remove from source workspace
        from_workspace.delete_knowledge_item(item_id)
        
        return True
    
    def clone_item(
        self,
        item_id: str,
        from_workspace_id: str,
        to_workspace_id: str,
    ) -> Optional[str]:
        """
        Clone a knowledge item to another workspace (keeps original).
        
        Args:
            item_id: ID of item to clone
            from_workspace_id: Source workspace ID
            to_workspace_id: Destination workspace ID
        
        Returns:
            New item ID in destination workspace
        """
        from_workspace = self.get_workspace(from_workspace_id)
        to_workspace = self.get_workspace(to_workspace_id)
        
        if not from_workspace or not to_workspace:
            return None
        
        item = from_workspace.get_knowledge_item(item_id)
        if not item:
            return None
        
        # Clone to destination workspace
        new_item_id = to_workspace.add_knowledge_item(
            content=item["content"],
            item_type=item["item_type"],
            metadata={
                **item["metadata"],
                "cloned_from": f"{from_workspace_id}:{item_id}",
            },
        )
        
        return new_item_id
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get statistics across all workspaces"""
        if not self.workspaces:
            return {
                "total_workspaces": 0,
                "total_items": 0,
                "by_type": {},
            }
        
        total_items = 0
        by_type = {}
        by_workspace_type = {}
        
        for workspace in self.workspaces.values():
            workspace_stats = workspace.get_statistics()
            total_items += workspace_stats["total_items"]
            
            # Aggregate by item type
            for item_type, count in workspace_stats["by_type"].items():
                by_type[item_type] = by_type.get(item_type, 0) + count
            
            # Aggregate by workspace type
            ws_type = workspace.workspace_type.value
            by_workspace_type[ws_type] = by_workspace_type.get(ws_type, 0) + 1
        
        return {
            "total_workspaces": len(self.workspaces),
            "total_items": total_items,
            "by_item_type": by_type,
            "by_workspace_type": by_workspace_type,
        }
    
    def verify_isolation(self, workspace_id: str) -> Dict[str, Any]:
        """
        Verify that workspace isolation is working correctly.
        
        Args:
            workspace_id: Workspace ID to verify
        
        Returns:
            Verification report
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return {
                "success": False,
                "error": "Workspace not found",
            }
        
        # Check that all items belong to this workspace
        items = workspace.get_all_items()
        foreign_items = [
            item for item in items
            if item.get("workspace_id") != workspace_id
        ]
        
        return {
            "success": True,
            "workspace_id": workspace_id,
            "total_items": len(items),
            "foreign_items": len(foreign_items),
            "isolation_verified": len(foreign_items) == 0,
            "cross_workspace_search_enabled": workspace.settings.get("allow_cross_workspace_search", False),
        }
