"""
Metadata System - Phase 5.6

Every knowledge item should store metadata:
- Source name
- File type
- Upload date
- Owner
- Workspace
- Project
- Tags
- Language
- Category
- Importance score
- Permission level
- Version number

This makes search, filtering, and access control much more reliable.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class PermissionLevel(Enum):
    """Permission levels for knowledge items"""
    PRIVATE = "private"
    WORKSPACE_ONLY = "workspace_only"
    TEAM_SHARED = "team_shared"
    SYSTEM_ACCESS = "system_access"
    PUBLIC_REFERENCE = "public_reference"


class MetadataSystem:
    """
    Manages metadata for knowledge items.
    Provides structured metadata storage, filtering, and access control.
    """
    
    def __init__(self):
        self.metadata_store: Dict[str, Dict[str, Any]] = {}
        self.next_metadata_id = 1
    
    def create_metadata(
        self,
        source_name: str,
        file_type: str,
        owner_id: int,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        language: str = "en",
        category: str = "general",
        importance_score: float = 0.5,
        permission_level: PermissionLevel = PermissionLevel.PRIVATE,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create metadata for a knowledge item.
        
        Args:
            source_name: Name of the source
            file_type: Type of file
            owner_id: Owner user ID
            workspace_id: Optional workspace ID
            project_id: Optional project ID
            tags: Optional tags
            language: Language of content
            category: Category of content
            importance_score: Importance score (0.0 to 1.0)
            permission_level: Permission level
            additional_metadata: Additional metadata fields
        
        Returns:
            Metadata ID
        """
        metadata_id = f"meta_{self.next_metadata_id}"
        self.next_metadata_id += 1
        
        metadata = {
            "metadata_id": metadata_id,
            "source_name": source_name,
            "file_type": file_type,
            "upload_date": datetime.utcnow().isoformat(),
            "owner_id": owner_id,
            "workspace_id": workspace_id,
            "project_id": project_id,
            "tags": tags or [],
            "language": language,
            "category": category,
            "importance_score": importance_score,
            "permission_level": permission_level.value,
            "version": 1,
            "version_history": [],
            **(additional_metadata or {}),
        }
        
        self.metadata_store[metadata_id] = metadata
        return metadata_id
    
    def get_metadata(self, metadata_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata by ID"""
        return self.metadata_store.get(metadata_id)
    
    def update_metadata(
        self,
        metadata_id: str,
        **updates,
    ) -> bool:
        """Update metadata fields"""
        metadata = self.metadata_store.get(metadata_id)
        if not metadata:
            return False
        
        # Save current version to history
        version_copy = metadata.copy()
        metadata["version_history"].append({
            "version": metadata["version"],
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": version_copy,
        })
        
        # Update fields
        for key, value in updates.items():
            if key in metadata or key in ["tags", "importance_score", "category"]:
                metadata[key] = value
        
        # Increment version
        metadata["version"] += 1
        
        return True
    
    def add_tag(self, metadata_id: str, tag: str):
        """Add a tag to metadata"""
        metadata = self.metadata_store.get(metadata_id)
        if metadata and tag not in metadata["tags"]:
            metadata["tags"].append(tag)
    
    def remove_tag(self, metadata_id: str, tag: str):
        """Remove a tag from metadata"""
        metadata = self.metadata_store.get(metadata_id)
        if metadata and tag in metadata["tags"]:
            metadata["tags"].remove(tag)
    
    def set_permission_level(
        self,
        metadata_id: str,
        permission_level: PermissionLevel,
    ):
        """Set permission level for metadata"""
        metadata = self.metadata_store.get(metadata_id)
        if metadata:
            metadata["permission_level"] = permission_level.value
    
    def update_importance_score(
        self,
        metadata_id: str,
        new_score: float,
    ):
        """Update importance score"""
        metadata = self.metadata_store.get(metadata_id)
        if metadata:
            metadata["importance_score"] = max(0.0, min(1.0, new_score))
    
    def filter_by_workspace(
        self,
        workspace_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all metadata for a specific workspace"""
        return [
            metadata for metadata in self.metadata_store.values()
            if metadata.get("workspace_id") == workspace_id
        ]
    
    def filter_by_project(
        self,
        project_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all metadata for a specific project"""
        return [
            metadata for metadata in self.metadata_store.values()
            if metadata.get("project_id") == project_id
        ]
    
    def filter_by_owner(
        self,
        owner_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all metadata for a specific owner"""
        return [
            metadata for metadata in self.metadata_store.values()
            if metadata.get("owner_id") == owner_id
        ]
    
    def filter_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
    ) -> List[Dict[str, Any]]:
        """Filter metadata by tags"""
        results = []
        
        for metadata in self.metadata_store.values():
            metadata_tags = set(metadata.get("tags", []))
            search_tags = set(tags)
            
            if match_all:
                if search_tags.issubset(metadata_tags):
                    results.append(metadata)
            else:
                if metadata_tags.intersection(search_tags):
                    results.append(metadata)
        
        return results
    
    def filter_by_category(
        self,
        category: str,
    ) -> List[Dict[str, Any]]:
        """Filter metadata by category"""
        return [
            metadata for metadata in self.metadata_store.values()
            if metadata.get("category") == category
        ]
    
    def filter_by_language(
        self,
        language: str,
    ) -> List[Dict[str, Any]]:
        """Filter metadata by language"""
        return [
            metadata for metadata in self.metadata_store.values()
            if metadata.get("language") == language
        ]
    
    def filter_by_permission_level(
        self,
        permission_level: PermissionLevel,
    ) -> List[Dict[str, Any]]:
        """Filter metadata by permission level"""
        return [
            metadata for metadata in self.metadata_store.values()
            if metadata.get("permission_level") == permission_level.value
        ]
    
    def filter_by_importance(
        self,
        min_score: float = 0.0,
        max_score: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """Filter metadata by importance score range"""
        return [
            metadata for metadata in self.metadata_store.values()
            if min_score <= metadata.get("importance_score", 0.0) <= max_score
        ]
    
    def search_metadata(
        self,
        query: str,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search metadata by query across specified fields.
        
        Args:
            query: Search query
            fields: Fields to search (default: source_name, tags, category)
        
        Returns:
            Matching metadata
        """
        if not fields:
            fields = ["source_name", "tags", "category"]
        
        query_lower = query.lower()
        results = []
        
        for metadata in self.metadata_store.values():
            for field in fields:
                value = metadata.get(field, "")
                if isinstance(value, str) and query_lower in value.lower():
                    results.append(metadata)
                    break
                elif isinstance(value, list):
                    if any(query_lower in str(item).lower() for item in value):
                        results.append(metadata)
                        break
        
        return results
    
    def get_version_history(
        self,
        metadata_id: str,
    ) -> List[Dict[str, Any]]:
        """Get version history for metadata"""
        metadata = self.metadata_store.get(metadata_id)
        if not metadata:
            return []
        return metadata.get("version_history", [])
    
    def restore_version(
        self,
        metadata_id: str,
        version: int,
    ) -> bool:
        """Restore metadata to a specific version"""
        metadata = self.metadata_store.get(metadata_id)
        if not metadata:
            return False
        
        for version_info in metadata["version_history"]:
            if version_info["version"] == version:
                # Restore the metadata
                old_metadata = version_info["metadata"]
                metadata.update(old_metadata)
                return True
        
        return False
    
    def delete_metadata(self, metadata_id: str) -> bool:
        """Delete metadata"""
        if metadata_id in self.metadata_store:
            del self.metadata_store[metadata_id]
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get metadata statistics"""
        if not self.metadata_store:
            return {
                "total_items": 0,
                "by_file_type": {},
                "by_category": {},
                "by_language": {},
                "by_permission_level": {},
            }
        
        by_file_type = {}
        by_category = {}
        by_language = {}
        by_permission_level = {}
        
        for metadata in self.metadata_store.values():
            # Count by file type
            file_type = metadata.get("file_type", "unknown")
            by_file_type[file_type] = by_file_type.get(file_type, 0) + 1
            
            # Count by category
            category = metadata.get("category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1
            
            # Count by language
            language = metadata.get("language", "unknown")
            by_language[language] = by_language.get(language, 0) + 1
            
            # Count by permission level
            permission = metadata.get("permission_level", "unknown")
            by_permission_level[permission] = by_permission_level.get(permission, 0) + 1
        
        return {
            "total_items": len(self.metadata_store),
            "by_file_type": by_file_type,
            "by_category": by_category,
            "by_language": by_language,
            "by_permission_level": by_permission_level,
        }
    
    def get_workspace_summary(self, workspace_id: str) -> Dict[str, Any]:
        """Get summary of metadata for a workspace"""
        workspace_metadata = self.filter_by_workspace(workspace_id)
        
        if not workspace_metadata:
            return {
                "workspace_id": workspace_id,
                "total_items": 0,
                "by_category": {},
                "total_importance": 0.0,
            }
        
        by_category = {}
        total_importance = 0.0
        
        for metadata in workspace_metadata:
            category = metadata.get("category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1
            total_importance += metadata.get("importance_score", 0.0)
        
        return {
            "workspace_id": workspace_id,
            "total_items": len(workspace_metadata),
            "by_category": by_category,
            "total_importance": total_importance,
            "average_importance": total_importance / len(workspace_metadata),
        }
