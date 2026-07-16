"""
Project Mode - Phase 4.5

Persistent workspaces for long-running AI workflows.
Each project contains:
- Goals
- Files
- Chats
- Tasks
- Knowledge base
- Timeline
- Notes
- Memory
- Version history
- Team members (future)

Capabilities:
- Continue work after days or weeks
- Track progress
- Generate implementation plans
- Break goals into milestones
- Suggest next tasks
- Maintain project-specific context automatically
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field


class ProjectStatus(Enum):
    """Status of a project"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(Enum):
    """Status of a task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class ProjectTask:
    """A task within a project"""
    task_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: str = "medium"
    assigned_to: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    estimated_hours: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    milestone_id: Optional[str] = None


@dataclass
class ProjectMilestone:
    """A milestone within a project"""
    milestone_id: str
    title: str
    description: str
    due_date: Optional[str] = None
    status: str = "pending"
    tasks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None


@dataclass
class ProjectFile:
    """A file within a project"""
    file_id: str
    name: str
    path: str
    file_type: str
    size: int
    uploaded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: int = 1


@dataclass
class ProjectChat:
    """A chat session within a project"""
    chat_id: str
    title: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    message_count: int = 0
    last_activity: Optional[str] = None


class ProjectWorkspace:
    """
    A persistent workspace for long-running projects.
    Maintains context across sessions and enables continuous work.
    """
    
    def __init__(
        self,
        project_id: str,
        name: str,
        description: str,
        user_id: int,
        workspace_type: str = "general",
    ):
        self.project_id = project_id
        self.name = name
        self.description = description
        self.user_id = user_id
        self.workspace_type = workspace_type
        self.status = ProjectStatus.ACTIVE
        
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
        
        # Project components
        self.goals: List[str] = []
        self.tasks: Dict[str, ProjectTask] = {}
        self.milestones: Dict[str, ProjectMilestone] = {}
        self.files: Dict[str, ProjectFile] = {}
        self.chats: Dict[str, ProjectChat] = {}
        self.notes: List[Dict[str, Any]] = []
        self.knowledge_base: List[Dict[str, Any]] = []
        self.timeline: List[Dict[str, Any]] = []
        self.memory: Dict[str, Any] = {}
        self.version_history: List[Dict[str, Any]] = []
        
        # Progress tracking
        self.progress_percentage: float = 0.0
        self.next_task_id = 1
        self.next_milestone_id = 1
        self.next_file_id = 1
        self.next_chat_id = 1
    
    def add_goal(self, goal: str):
        """Add a goal to the project"""
        if goal not in self.goals:
            self.goals.append(goal)
            self._add_timeline_event("goal_added", {"goal": goal})
            self._updated()
    
    def remove_goal(self, goal: str):
        """Remove a goal from the project"""
        if goal in self.goals:
            self.goals.remove(goal)
            self._add_timeline_event("goal_removed", {"goal": goal})
            self._updated()
    
    def create_task(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        milestone_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        estimated_hours: float = 0.0,
    ) -> ProjectTask:
        """Create a new task"""
        task_id = f"task_{self.next_task_id}"
        self.next_task_id += 1
        
        task = ProjectTask(
            task_id=task_id,
            title=title,
            description=description,
            priority=priority,
            milestone_id=milestone_id,
            dependencies=dependencies or [],
            estimated_hours=estimated_hours,
        )
        
        self.tasks[task_id] = task
        
        # Add to milestone if specified
        if milestone_id and milestone_id in self.milestones:
            self.milestones[milestone_id].tasks.append(task_id)
        
        self._add_timeline_event("task_created", {"task_id": task_id, "title": title})
        self._updated()
        self._recalculate_progress()
        
        return task
    
    def update_task_status(self, task_id: str, status: TaskStatus):
        """Update the status of a task"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            if status == TaskStatus.COMPLETED:
                self.tasks[task_id].completed_at = datetime.utcnow().isoformat()
            
            self._add_timeline_event("task_updated", {"task_id": task_id, "status": status.value})
            self._updated()
            self._recalculate_progress()
    
    def create_milestone(
        self,
        title: str,
        description: str,
        due_date: Optional[str] = None,
    ) -> ProjectMilestone:
        """Create a new milestone"""
        milestone_id = f"milestone_{self.next_milestone_id}"
        self.next_milestone_id += 1
        
        milestone = ProjectMilestone(
            milestone_id=milestone_id,
            title=title,
            description=description,
            due_date=due_date,
        )
        
        self.milestones[milestone_id] = milestone
        self._add_timeline_event("milestone_created", {"milestone_id": milestone_id, "title": title})
        self._updated()
        
        return milestone
    
    def complete_milestone(self, milestone_id: str):
        """Mark a milestone as completed"""
        if milestone_id in self.milestones:
            self.milestones[milestone_id].status = "completed"
            self.milestones[milestone_id].completed_at = datetime.utcnow().isoformat()
            self._add_timeline_event("milestone_completed", {"milestone_id": milestone_id})
            self._updated()
            self._recalculate_progress()
    
    def add_file(
        self,
        name: str,
        path: str,
        file_type: str,
        size: int,
    ) -> ProjectFile:
        """Add a file to the project"""
        file_id = f"file_{self.next_file_id}"
        self.next_file_id += 1
        
        file = ProjectFile(
            file_id=file_id,
            name=name,
            path=path,
            file_type=file_type,
            size=size,
        )
        
        self.files[file_id] = file
        self._add_timeline_event("file_added", {"file_id": file_id, "name": name})
        self._updated()
        
        return file
    
    def remove_file(self, file_id: str):
        """Remove a file from the project"""
        if file_id in self.files:
            file_name = self.files[file_id].name
            del self.files[file_id]
            self._add_timeline_event("file_removed", {"file_id": file_id, "name": file_name})
            self._updated()
    
    def create_chat(self, title: str) -> ProjectChat:
        """Create a new chat session"""
        chat_id = f"chat_{self.next_chat_id}"
        self.next_chat_id += 1
        
        chat = ProjectChat(
            chat_id=chat_id,
            title=title,
        )
        
        self.chats[chat_id] = chat
        self._add_timeline_event("chat_created", {"chat_id": chat_id, "title": title})
        self._updated()
        
        return chat
    
    def add_note(self, content: str, tags: Optional[List[str]] = None):
        """Add a note to the project"""
        note = {
            "note_id": len(self.notes),
            "content": content,
            "tags": tags or [],
            "created_at": datetime.utcnow().isoformat(),
        }
        self.notes.append(note)
        self._add_timeline_event("note_added", {"note_id": note["note_id"]})
        self._updated()
    
    def add_knowledge(self, title: str, content: str, source: Optional[str] = None):
        """Add knowledge to the project knowledge base"""
        knowledge = {
            "knowledge_id": len(self.knowledge_base),
            "title": title,
            "content": content,
            "source": source,
            "added_at": datetime.utcnow().isoformat(),
        }
        self.knowledge_base.append(knowledge)
        self._add_timeline_event("knowledge_added", {"knowledge_id": knowledge["knowledge_id"], "title": title})
        self._updated()
    
    def set_memory(self, key: str, value: Any):
        """Set a project-specific memory"""
        self.memory[key] = value
        self._updated()
    
    def get_memory(self, key: str) -> Optional[Any]:
        """Get a project-specific memory"""
        return self.memory.get(key)
    
    def generate_implementation_plan(self) -> Dict[str, Any]:
        """Generate an implementation plan from goals and tasks"""
        # Group tasks by milestone
        milestone_tasks = {}
        for milestone_id, milestone in self.milestones.items():
            milestone_tasks[milestone_id] = [
                self.tasks[task_id] for task_id in milestone.tasks
                if task_id in self.tasks
            ]
        
        # Tasks without milestones
        unassigned_tasks = [
            task for task in self.tasks.values()
            if not task.milestone_id or task.milestone_id not in self.milestones
        ]
        
        return {
            "goals": self.goals,
            "milestones": [
                {
                    "milestone_id": mid,
                    "title": self.milestones[mid].title,
                    "tasks": [
                        {
                            "task_id": task.task_id,
                            "title": task.title,
                            "status": task.status.value,
                            "priority": task.priority,
                        }
                        for task in tasks
                    ]
                }
                for mid, tasks in milestone_tasks.items()
            ],
            "unassigned_tasks": [
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "status": task.status.value,
                }
                for task in unassigned_tasks
            ],
            "overall_progress": self.progress_percentage,
            "estimated_total_hours": sum(task.estimated_hours for task in self.tasks.values()),
        }
    
    def suggest_next_tasks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Suggest next tasks to work on"""
        suggestions = []
        
        # Get pending tasks with no unmet dependencies
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                # Check dependencies
                dependencies_met = all(
                    self.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                    if dep_id in self.tasks
                )
                
                if dependencies_met:
                    suggestions.append({
                        "task_id": task.task_id,
                        "title": task.title,
                        "description": task.description,
                        "priority": task.priority,
                        "estimated_hours": task.estimated_hours,
                    })
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda t: priority_order.get(t["priority"], 3))
        
        return suggestions[:limit]
    
    def _recalculate_progress(self):
        """Recalculate overall project progress"""
        if not self.tasks:
            self.progress_percentage = 0.0
            return
        
        completed_tasks = sum(
            1 for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED
        )
        
        self.progress_percentage = (completed_tasks / len(self.tasks)) * 100
    
    def _add_timeline_event(self, event_type: str, data: Dict[str, Any]):
        """Add an event to the project timeline"""
        event = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.timeline.append(event)
    
    def _updated(self):
        """Mark project as updated"""
        self.updated_at = datetime.utcnow().isoformat()
        
        # Create version snapshot (simplified)
        self.version_history.append({
            "version": len(self.version_history) + 1,
            "timestamp": self.updated_at,
            "task_count": len(self.tasks),
            "milestone_count": len(self.milestones),
            "file_count": len(self.files),
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the project"""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "workspace_type": self.workspace_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "goals": self.goals,
            "progress": {
                "percentage": self.progress_percentage,
                "total_tasks": len(self.tasks),
                "completed_tasks": sum(
                    1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED
                ),
                "total_milestones": len(self.milestones),
                "completed_milestones": sum(
                    1 for m in self.milestones.values() if m.status == "completed"
                ),
            },
            "resources": {
                "files": len(self.files),
                "chats": len(self.chats),
                "notes": len(self.notes),
                "knowledge_items": len(self.knowledge_base),
            },
            "activity": {
                "timeline_events": len(self.timeline),
                "last_activity": self.timeline[-1]["timestamp"] if self.timeline else None,
            },
        }


class ProjectManager:
    """
    Manages multiple project workspaces.
    Provides project lifecycle management and coordination.
    """
    
    def __init__(self):
        self.projects: Dict[str, ProjectWorkspace] = {}
        self.next_project_id = 1
    
    def create_project(
        self,
        name: str,
        description: str,
        user_id: int,
        workspace_type: str = "general",
        goals: Optional[List[str]] = None,
    ) -> ProjectWorkspace:
        """Create a new project workspace"""
        project_id = f"project_{self.next_project_id}"
        self.next_project_id += 1
        
        project = ProjectWorkspace(
            project_id=project_id,
            name=name,
            description=description,
            user_id=user_id,
            workspace_type=workspace_type,
        )
        
        if goals:
            for goal in goals:
                project.add_goal(goal)
        
        self.projects[project_id] = project
        return project
    
    def get_project(self, project_id: str) -> Optional[ProjectWorkspace]:
        """Get a project by ID"""
        return self.projects.get(project_id)
    
    def get_user_projects(
        self,
        user_id: int,
        status: Optional[ProjectStatus] = None,
    ) -> List[ProjectWorkspace]:
        """Get all projects for a user, optionally filtered by status"""
        user_projects = [
            project for project in self.projects.values()
            if project.user_id == user_id
        ]
        
        if status:
            user_projects = [p for p in user_projects if p.status == status]
        
        return user_projects
    
    def update_project_status(self, project_id: str, status: ProjectStatus):
        """Update project status"""
        if project_id in self.projects:
            self.projects[project_id].status = status
    
    def delete_project(self, project_id: str):
        """Delete a project"""
        if project_id in self.projects:
            del self.projects[project_id]
    
    def archive_project(self, project_id: str):
        """Archive a project"""
        if project_id in self.projects:
            self.projects[project_id].status = ProjectStatus.ARCHIVED
    
    def get_project_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get statistics about user's projects"""
        user_projects = self.get_user_projects(user_id)
        
        total_tasks = sum(len(p.tasks) for p in user_projects)
        completed_tasks = sum(
            sum(1 for t in p.tasks.values() if t.status == TaskStatus.COMPLETED)
            for p in user_projects
        )
        
        by_status = {}
        for project in user_projects:
            status = project.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_projects": len(user_projects),
            "by_status": by_status,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "overall_completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        }
