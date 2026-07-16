"""
Workspace Memory - Phase 3.2 Layer 6

Each workspace has isolated memory:
- School: Assignments, notes, PDFs, study plans
- Business: Meetings, clients, financial reports, strategy documents

Information should not leak between workspaces unless the user explicitly links them.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class WorkspaceType(Enum):
    """Types of workspaces"""
    PERSONAL = "personal"
    WORK = "work"
    SCHOOL = "school"
    PROJECT = "project"
    RESEARCH = "research"


class WorkspaceMemory:
    """
    Manages isolated memory for different workspaces.
    Ensures information doesn't leak between workspaces.
    """
    
    def __init__(self):
        self.workspaces: Dict[str, Dict[str, Any]] = {}
        self.workspace_data: Dict[str, Dict[str, Any]] = {}
        self.next_workspace_id = 1
    
    def create_workspace(
        self,
        user_id: int,
        name: str,
        workspace_type: WorkspaceType,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new workspace.
        
        Args:
            user_id: User ID
            name: Workspace name
            workspace_type: Type of workspace
            description: Optional description
            metadata: Additional metadata
        
        Returns:
            Workspace ID
        """
        workspace_id = f"workspace_{self.next_workspace_id}"
        self.next_workspace_id += 1
        
        self.workspaces[workspace_id] = {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "name": name,
            "type": workspace_type.value,
            "description": description or "",
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "linked_workspaces": [],
        }
        
        self.workspace_data[workspace_id] = {
            "notes": [],
            "files": [],
            "tasks": [],
            "documents": [],
            "settings": {},
        }
        
        return workspace_id
    
    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace metadata"""
        return self.workspaces.get(workspace_id)
    
    def get_user_workspaces(
        self,
        user_id: int,
        workspace_type: Optional[WorkspaceType] = None,
    ) -> List[Dict[str, Any]]:
        """Get all workspaces for a user, optionally filtered by type"""
        user_workspaces = [
            ws for ws in self.workspaces.values()
            if ws["user_id"] == user_id
        ]
        
        if workspace_type:
            user_workspaces = [
                ws for ws in user_workspaces
                if ws["type"] == workspace_type.value
            ]
        
        return user_workspaces
    
    def update_workspace(
        self,
        workspace_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Update workspace metadata"""
        if workspace_id in self.workspaces:
            if name is not None:
                self.workspaces[workspace_id]["name"] = name
            if description is not None:
                self.workspaces[workspace_id]["description"] = description
            if metadata is not None:
                self.workspaces[workspace_id]["metadata"] = metadata
            self.workspaces[workspace_id]["updated_at"] = datetime.utcnow().isoformat()
    
    def delete_workspace(self, workspace_id: str):
        """Delete a workspace and all its data"""
        if workspace_id in self.workspaces:
            del self.workspaces[workspace_id]
        if workspace_id in self.workspace_data:
            del self.workspace_data[workspace_id]
    
    def link_workspaces(self, workspace_id_1: str, workspace_id_2: str):
        """Link two workspaces to allow information sharing"""
        if workspace_id_1 in self.workspaces and workspace_id_2 in self.workspaces:
            if workspace_id_2 not in self.workspaces[workspace_id_1]["linked_workspaces"]:
                self.workspaces[workspace_id_1]["linked_workspaces"].append(workspace_id_2)
            if workspace_id_1 not in self.workspaces[workspace_id_2]["linked_workspaces"]:
                self.workspaces[workspace_id_2]["linked_workspaces"].append(workspace_id_1)
    
    def unlink_workspaces(self, workspace_id_1: str, workspace_id_2: str):
        """Unlink two workspaces"""
        if workspace_id_1 in self.workspaces:
            self.workspaces[workspace_id_1]["linked_workspaces"] = [
                ws for ws in self.workspaces[workspace_id_1]["linked_workspaces"]
                if ws != workspace_id_2
            ]
        if workspace_id_2 in self.workspaces:
            self.workspaces[workspace_id_2]["linked_workspaces"] = [
                ws for ws in self.workspaces[workspace_id_2]["linked_workspaces"]
                if ws != workspace_id_1
            ]
    
    # Data management methods
    
    def add_note(
        self,
        workspace_id: str,
        note: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add a note to a workspace"""
        if workspace_id in self.workspace_data:
            self.workspace_data[workspace_id]["notes"].append({
                "note_id": len(self.workspace_data[workspace_id]["notes"]),
                "title": title or "Untitled",
                "content": note,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            })
    
    def get_notes(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all notes from a workspace"""
        if workspace_id in self.workspace_data:
            return self.workspace_data[workspace_id]["notes"]
        return []
    
    def add_file(
        self,
        workspace_id: str,
        file_name: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add a file to a workspace"""
        if workspace_id in self.workspace_data:
            self.workspace_data[workspace_id]["files"].append({
                "file_id": len(self.workspace_data[workspace_id]["files"]),
                "name": file_name,
                "path": file_path,
                "metadata": metadata or {},
                "added_at": datetime.utcnow().isoformat(),
            })
    
    def get_files(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all files from a workspace"""
        if workspace_id in self.workspace_data:
            return self.workspace_data[workspace_id]["files"]
        return []
    
    def add_task(
        self,
        workspace_id: str,
        task: str,
        priority: str = "medium",
        due_date: Optional[str] = None,
    ):
        """Add a task to a workspace"""
        if workspace_id in self.workspace_data:
            self.workspace_data[workspace_id]["tasks"].append({
                "task_id": len(self.workspace_data[workspace_id]["tasks"]),
                "task": task,
                "priority": priority,
                "due_date": due_date,
                "completed": False,
                "created_at": datetime.utcnow().isoformat(),
            })
    
    def get_tasks(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all tasks from a workspace"""
        if workspace_id in self.workspace_data:
            return self.workspace_data[workspace_id]["tasks"]
        return []
    
    def complete_task(self, workspace_id: str, task_id: int):
        """Mark a task as completed"""
        if workspace_id in self.workspace_data:
            for task in self.workspace_data[workspace_id]["tasks"]:
                if task["task_id"] == task_id:
                    task["completed"] = True
                    task["completed_at"] = datetime.utcnow().isoformat()
    
    def add_document(
        self,
        workspace_id: str,
        document_name: str,
        document_content: str,
        document_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add a document to a workspace"""
        if workspace_id in self.workspace_data:
            self.workspace_data[workspace_id]["documents"].append({
                "document_id": len(self.workspace_data[workspace_id]["documents"]),
                "name": document_name,
                "content": document_content,
                "type": document_type,
                "metadata": metadata or {},
                "added_at": datetime.utcnow().isoformat(),
            })
    
    def get_documents(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all documents from a workspace"""
        if workspace_id in self.workspace_data:
            return self.workspace_data[workspace_id]["documents"]
        return []
    
    def set_workspace_setting(
        self,
        workspace_id: str,
        setting_key: str,
        setting_value: Any,
    ):
        """Set a workspace-specific setting"""
        if workspace_id in self.workspace_data:
            self.workspace_data[workspace_id]["settings"][setting_key] = setting_value
    
    def get_workspace_setting(
        self,
        workspace_id: str,
        setting_key: str,
    ) -> Optional[Any]:
        """Get a workspace-specific setting"""
        if workspace_id in self.workspace_data:
            return self.workspace_data[workspace_id]["settings"].get(setting_key)
        return None
    
    def search_workspace(
        self,
        workspace_id: str,
        query: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search within a workspace.
        
        Args:
            workspace_id: Workspace ID
            query: Search query
        
        Returns:
            Dictionary with results by type
        """
        if workspace_id not in self.workspace_data:
            return {}
        
        query_lower = query.lower()
        results = {
            "notes": [],
            "files": [],
            "tasks": [],
            "documents": [],
        }
        
        # Search notes
        for note in self.workspace_data[workspace_id]["notes"]:
            if query_lower in note["content"].lower() or query_lower in note["title"].lower():
                results["notes"].append(note)
        
        # Search files
        for file in self.workspace_data[workspace_id]["files"]:
            if query_lower in file["name"].lower():
                results["files"].append(file)
        
        # Search tasks
        for task in self.workspace_data[workspace_id]["tasks"]:
            if query_lower in task["task"].lower():
                results["tasks"].append(task)
        
        # Search documents
        for doc in self.workspace_data[workspace_id]["documents"]:
            if query_lower in doc["content"].lower() or query_lower in doc["name"].lower():
                results["documents"].append(doc)
        
        return results
    
    def get_workspace_summary(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a workspace"""
        if workspace_id not in self.workspaces:
            return None
        
        workspace = self.workspaces[workspace_id]
        data = self.workspace_data.get(workspace_id, {})
        
        return {
            "workspace_id": workspace_id,
            "name": workspace["name"],
            "type": workspace["type"],
            "total_notes": len(data.get("notes", [])),
            "total_files": len(data.get("files", [])),
            "total_tasks": len(data.get("tasks", [])),
            "completed_tasks": sum(1 for t in data.get("tasks", []) if t["completed"]),
            "total_documents": len(data.get("documents", [])),
            "linked_workspaces": len(workspace.get("linked_workspaces", [])),
        }
