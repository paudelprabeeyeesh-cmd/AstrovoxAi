"""Intelligent Workspace API — projects, notes, tasks, memory, dashboards.

Stage 21 Step 3 — exposes workspace-scoped features over FastAPI.
"""

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional

from .auth_utils import get_user_id_from_token
from .enterprise.service import org_service
from .enterprise.rbac import rbac
from .workspace import workspace_manager


router = APIRouter(prefix="/api/workspaces", tags=["workspace"])


# ============================================================================
# Request Models
# ============================================================================

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    tags: Optional[list[str]] = None


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class CreateNoteRequest(BaseModel):
    title: str
    content: Optional[str] = ""
    project_id: Optional[str] = ""
    tags: Optional[list[str]] = None


class UpdateNoteRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    assignee_id: Optional[str] = ""
    project_id: Optional[str] = ""
    priority: Optional[str] = "medium"
    due_date: Optional[float] = 0.0
    dependencies: Optional[list[str]] = None
    estimated_hours: Optional[float] = 0.0
    tags: Optional[list[str]] = None


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    logged_hours: Optional[float] = None


class AddMemoryRequest(BaseModel):
    content: str
    category: Optional[str] = "general"
    importance: Optional[float] = 0.5
    source: Optional[str] = ""
    source_id: Optional[str] = ""


class CreateConversationRequest(BaseModel):
    title: str
    project_id: Optional[str] = ""
    is_ai_session: Optional[bool] = False
    participants: Optional[list[str]] = None


class AddMessageRequest(BaseModel):
    content: str
    role: Optional[str] = "user"
    branch_id: Optional[str] = ""


class BranchConversationRequest(BaseModel):
    name: Optional[str] = "branch"
    parent_branch_id: Optional[str] = ""


class CreateFileRequest(BaseModel):
    name: str
    url: Optional[str] = ""
    size_bytes: Optional[int] = 0
    content_type: Optional[str] = ""
    description: Optional[str] = ""


class CreateThreadRequest(BaseModel):
    resource_type: str
    resource_id: str
    title: Optional[str] = ""
    initial_message: Optional[str] = ""


class ThreadReplyRequest(BaseModel):
    content: str


class RecommendationsRequest(BaseModel):
    context: Optional[str] = ""
    max_recommendations: Optional[int] = Field(default=10, le=50)


class AddWidgetRequest(BaseModel):
    widget_type: str
    title: str
    config: Optional[dict] = None


class ProjectMemoryRequest(BaseModel):
    content: str
    category: Optional[str] = "context"


# ============================================================================
# Permission helper
# ============================================================================

def _require_workspace_read(user_id: str, workspace_id: str) -> None:
    """Verify the user can read this workspace or raise 403/404."""
    ws = org_service.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if not rbac.has_workspace_permission(user_id, workspace_id, "workspace:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _require_workspace_write(user_id: str, workspace_id: str) -> None:
    """Verify the user can write to this workspace or raise 403/404."""
    ws = org_service.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if not rbac.has_workspace_permission(user_id, workspace_id, "workspace:write"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ============================================================================
# Projects
# ============================================================================

@router.post("/{workspace_id}/projects")
async def create_project(workspace_id: str, request: CreateProjectRequest, authorization: str = Header(None)):
    """Create a new AI project in a workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    project = workspace_manager.create_project(
        workspace_id=workspace_id,
        name=request.name,
        owner_id=user_id,
        description=request.description or "",
        tags=request.tags,
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create project")

    return {
        "status": "OK",
        "project": {
            "id": project.id,
            "workspace_id": project.workspace_id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "tags": project.tags,
            "summary": project.summary,
            "owner_id": project.owner_id,
            "created_at": project.created_at,
        },
    }


@router.get("/{workspace_id}/projects")
async def list_projects(
    workspace_id: str,
    status: Optional[str] = Query(default=""),
    authorization: str = Header(None),
):
    """List projects in a workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    projects = workspace_manager.list_projects(workspace_id, status=status)
    return {
        "status": "OK",
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "status": p.status,
                "tags": p.tags,
                "summary": p.summary,
                "owner_id": p.owner_id,
                "task_count": p.task_count,
                "note_count": p.note_count,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for p in projects
        ],
    }


@router.get("/{workspace_id}/projects/{project_id}")
async def get_project(workspace_id: str, project_id: str, authorization: str = Header(None)):
    """Get a single project."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    project = workspace_manager.get_project(project_id)
    if not project or project.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return {
        "status": "OK",
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "tags": project.tags,
            "summary": project.summary,
            "owner_id": project.owner_id,
            "task_count": project.task_count,
            "note_count": project.note_count,
            "memory": project.memory,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        },
    }


@router.patch("/{workspace_id}/projects/{project_id}")
async def update_project(
    workspace_id: str,
    project_id: str,
    request: UpdateProjectRequest,
    authorization: str = Header(None),
):
    """Update a project."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    project = workspace_manager.get_project(project_id)
    if not project or project.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project = workspace_manager.update_project(
        project_id,
        name=request.name,
        description=request.description,
        status=request.status,
    )
    return {"status": "OK", "project_id": project.id, "status_value": project.status}


@router.delete("/{workspace_id}/projects/{project_id}")
async def delete_project(workspace_id: str, project_id: str, authorization: str = Header(None)):
    """Delete a project."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    project = workspace_manager.get_project(project_id)
    if not project or project.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not workspace_manager.delete_project(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete")

    return {"status": "OK", "message": "Project deleted"}


@router.post("/{workspace_id}/projects/{project_id}/memory")
async def add_project_memory(
    workspace_id: str,
    project_id: str,
    request: ProjectMemoryRequest,
    authorization: str = Header(None),
):
    """Add a memory entry to a project."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    entry = workspace_manager.add_project_memory(
        project_id=project_id,
        user_id=user_id,
        content=request.content,
        category=request.category or "context",
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return {"status": "OK", "memory_id": entry.id}


# ============================================================================
# Notes
# ============================================================================

@router.post("/{workspace_id}/notes")
async def create_note(workspace_id: str, request: CreateNoteRequest, authorization: str = Header(None)):
    """Create a new note."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    note = workspace_manager.create_note(
        workspace_id=workspace_id,
        title=request.title,
        author_id=user_id,
        content=request.content or "",
        project_id=request.project_id or "",
        tags=request.tags,
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create note")

    return {
        "status": "OK",
        "note": {
            "id": note.id,
            "title": note.title,
            "workspace_id": note.workspace_id,
            "project_id": note.project_id,
            "author_id": note.author_id,
            "tags": note.tags,
            "version_count": len(note.versions),
            "created_at": note.created_at,
        },
    }


@router.get("/{workspace_id}/notes")
async def list_notes(
    workspace_id: str,
    project_id: Optional[str] = Query(default=""),
    authorization: str = Header(None),
):
    """List notes in a workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    notes = workspace_manager.list_notes(workspace_id, project_id=project_id)
    return {
        "status": "OK",
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "author_id": n.author_id,
                "project_id": n.project_id,
                "tags": n.tags,
                "is_pinned": n.is_pinned,
                "version_count": len(n.versions),
                "updated_at": n.updated_at,
            }
            for n in notes
        ],
    }


@router.get("/{workspace_id}/notes/{note_id}")
async def get_note(workspace_id: str, note_id: str, authorization: str = Header(None)):
    """Get a single note including version history."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    note = workspace_manager.get_note(note_id)
    if not note or note.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    return {
        "status": "OK",
        "note": {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "project_id": note.project_id,
            "tags": note.tags,
            "collaborators": note.collaborators,
            "versions": [
                {
                    "id": v.id,
                    "version_number": v.version_number,
                    "author_id": v.author_id,
                    "created_at": v.created_at,
                }
                for v in note.versions
            ],
            "updated_at": note.updated_at,
        },
    }


@router.patch("/{workspace_id}/notes/{note_id}")
async def update_note(
    workspace_id: str,
    note_id: str,
    request: UpdateNoteRequest,
    authorization: str = Header(None),
):
    """Update a note (creates a new version when content changes)."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    note = workspace_manager.get_note(note_id)
    if not note or note.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    note = workspace_manager.update_note(
        note_id,
        user_id=user_id,
        content=request.content,
        title=request.title,
    )
    return {"status": "OK", "note_id": note.id, "version_count": len(note.versions)}


@router.delete("/{workspace_id}/notes/{note_id}")
async def delete_note(workspace_id: str, note_id: str, authorization: str = Header(None)):
    """Delete a note."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    note = workspace_manager.get_note(note_id)
    if not note or note.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if not workspace_manager.delete_note(note_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete")

    return {"status": "OK", "message": "Note deleted"}


# ============================================================================
# Tasks
# ============================================================================

@router.post("/{workspace_id}/tasks")
async def create_task(workspace_id: str, request: CreateTaskRequest, authorization: str = Header(None)):
    """Create a new task."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    task = workspace_manager.create_task(
        workspace_id=workspace_id,
        title=request.title,
        created_by=user_id,
        description=request.description or "",
        assignee_id=request.assignee_id or "",
        project_id=request.project_id or "",
        priority=request.priority or "medium",
        due_date=request.due_date or 0.0,
        dependencies=request.dependencies,
        estimated_hours=request.estimated_hours or 0.0,
        tags=request.tags,
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create task")

    return {
        "status": "OK",
        "task": {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "assignee_id": task.assignee_id,
            "project_id": task.project_id,
            "created_at": task.created_at,
        },
    }


@router.get("/{workspace_id}/tasks")
async def list_tasks(
    workspace_id: str,
    project_id: Optional[str] = Query(default=""),
    task_status: Optional[str] = Query(default="", alias="status"),
    assignee_id: Optional[str] = Query(default=""),
    authorization: str = Header(None),
):
    """List tasks with optional filters."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    tasks = workspace_manager.list_tasks(
        workspace_id,
        project_id=project_id,
        status=task_status,
        assignee_id=assignee_id,
    )
    return {
        "status": "OK",
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "assignee_id": t.assignee_id,
                "project_id": t.project_id,
                "dependencies": t.dependencies,
                "tags": t.tags,
                "due_date": t.due_date,
                "estimated_hours": t.estimated_hours,
                "logged_hours": t.logged_hours,
                "ai_suggested": t.ai_suggested,
                "completed_at": t.completed_at,
            }
            for t in tasks
        ],
    }


@router.patch("/{workspace_id}/tasks/{task_id}")
async def update_task(
    workspace_id: str,
    task_id: str,
    request: UpdateTaskRequest,
    authorization: str = Header(None),
):
    """Update a task."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    task = workspace_manager.get_task(task_id)
    if not task or task.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task = workspace_manager.update_task(
        task_id,
        title=request.title,
        description=request.description,
        status=request.status,
        priority=request.priority,
        assignee_id=request.assignee_id,
        logged_hours=request.logged_hours,
    )
    return {"status": "OK", "task_id": task.id, "status_value": task.status}


@router.delete("/{workspace_id}/tasks/{task_id}")
async def delete_task(workspace_id: str, task_id: str, authorization: str = Header(None)):
    """Delete a task."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    task = workspace_manager.get_task(task_id)
    if not task or task.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if not workspace_manager.delete_task(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete")

    return {"status": "OK", "message": "Task deleted"}


@router.post("/{workspace_id}/tasks/suggest")
async def suggest_tasks(
    workspace_id: str,
    project_id: Optional[str] = Query(default=""),
    context: Optional[str] = Query(default=""),
    max_suggestions: Optional[int] = Query(default=5, le=20),
    authorization: str = Header(None),
):
    """Get AI-suggested tasks for a workspace or project."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    suggestions = workspace_manager.suggest_tasks(
        workspace_id,
        project_id=project_id,
        context=context,
        max_suggestions=max_suggestions,
    )
    return {
        "status": "OK",
        "suggestions": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "tags": t.tags,
                "ai_suggested": True,
            }
            for t in suggestions
        ],
    }


@router.get("/{workspace_id}/projects/{project_id}/analytics")
async def project_analytics(workspace_id: str, project_id: str, authorization: str = Header(None)):
    """Get analytics for a project."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    analytics = workspace_manager.get_project_analytics(project_id)
    if not analytics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return {"status": "OK", "analytics": analytics}


# ============================================================================
# Workspace Memory
# ============================================================================

@router.post("/{workspace_id}/memory")
async def add_memory(workspace_id: str, request: AddMemoryRequest, authorization: str = Header(None)):
    """Add a shared memory entry to the workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    entry = workspace_manager.add_memory(
        workspace_id=workspace_id,
        user_id=user_id,
        content=request.content,
        category=request.category or "general",
        importance=request.importance or 0.5,
        source=request.source or "",
        source_id=request.source_id or "",
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to add memory")

    return {"status": "OK", "memory_id": entry.id}


@router.get("/{workspace_id}/memory")
async def list_memory(
    workspace_id: str,
    category: Optional[str] = Query(default=""),
    min_importance: Optional[float] = Query(default=0.0),
    authorization: str = Header(None),
):
    """List memory entries in the workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    entries = workspace_manager.get_workspace_memory(
        workspace_id,
        category=category,
        min_importance=min_importance,
    )
    return {
        "status": "OK",
        "memory": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "content": e.content,
                "category": e.category,
                "importance": e.importance,
                "source": e.source,
                "created_at": e.created_at,
            }
            for e in entries
        ],
    }


@router.post("/{workspace_id}/memory/consolidate")
async def consolidate_memory(workspace_id: str, authorization: str = Header(None)):
    """Consolidate similar memory entries in a workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    consolidated = workspace_manager.consolidate_memory(workspace_id)
    return {
        "status": "OK",
        "consolidated_count": len(consolidated),
    }


@router.post("/{workspace_id}/context")
async def share_context(workspace_id: str, request: AddMemoryRequest, authorization: str = Header(None)):
    """Share a piece of context with the workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    entry = workspace_manager.share_context(
        workspace_id=workspace_id,
        user_id=user_id,
        content=request.content,
        category=request.category or "context",
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to share context")

    return {"status": "OK", "context_id": entry.id}


# ============================================================================
# Shared Conversations
# ============================================================================

@router.post("/{workspace_id}/conversations")
async def create_conversation(
    workspace_id: str,
    request: CreateConversationRequest,
    authorization: str = Header(None),
):
    """Create a shared conversation in a workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    conversation = workspace_manager.create_conversation(
        workspace_id=workspace_id,
        title=request.title,
        created_by=user_id,
        project_id=request.project_id or "",
        is_ai_session=request.is_ai_session or False,
        participants=request.participants,
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create conversation")

    return {
        "status": "OK",
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "workspace_id": conversation.workspace_id,
            "project_id": conversation.project_id,
            "is_ai_session": conversation.is_ai_session,
            "participants": conversation.participants,
            "active_branch_id": conversation.active_branch_id,
            "created_at": conversation.created_at,
        },
    }


@router.get("/{workspace_id}/conversations")
async def list_conversations(
    workspace_id: str,
    project_id: Optional[str] = Query(default=""),
    authorization: str = Header(None),
):
    """List shared conversations."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    conversations = workspace_manager.list_conversations(workspace_id, project_id=project_id)
    return {
        "status": "OK",
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "project_id": c.project_id,
                "is_ai_session": c.is_ai_session,
                "participants": c.participants,
                "branch_count": len(c.branches),
                "updated_at": c.updated_at,
            }
            for c in conversations
        ],
    }


@router.post("/{workspace_id}/conversations/{conversation_id}/messages")
async def add_conversation_message(
    workspace_id: str,
    conversation_id: str,
    request: AddMessageRequest,
    authorization: str = Header(None),
):
    """Append a message to a shared conversation."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    message = workspace_manager.add_message(
        conversation_id=conversation_id,
        user_id=user_id,
        content=request.content,
        role=request.role or "user",
        branch_id=request.branch_id or "",
    )
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    return {"status": "OK", "message": message}


@router.post("/{workspace_id}/conversations/{conversation_id}/branches")
async def branch_conversation(
    workspace_id: str,
    conversation_id: str,
    request: BranchConversationRequest,
    authorization: str = Header(None),
):
    """Branch a shared conversation."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    branch = workspace_manager.branch_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
        name=request.name or "branch",
        parent_branch_id=request.parent_branch_id or "",
    )
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    return {
        "status": "OK",
        "branch": {
            "id": branch.id,
            "name": branch.name,
            "parent_branch_id": branch.parent_branch_id,
            "created_at": branch.created_at,
        },
    }


# ============================================================================
# Activity, Recommendations, Dashboard
# ============================================================================

@router.get("/{workspace_id}/activity")
async def activity_timeline(
    workspace_id: str,
    resource_type: Optional[str] = Query(default=""),
    user_id: Optional[str] = Query(default=""),
    since: Optional[float] = Query(default=0.0),
    limit: Optional[int] = Query(default=50, le=200),
    authorization: str = Header(None),
):
    """Get aggregated activity timeline for the workspace."""
    caller_id = get_user_id_from_token(authorization)
    _require_workspace_read(caller_id, workspace_id)

    events = workspace_manager.get_activity_timeline(
        workspace_id,
        resource_type=resource_type,
        user_id=user_id,
        since=since,
        limit=limit,
    )
    return {"status": "OK", "events": events, "count": len(events)}


@router.post("/{workspace_id}/recommendations")
async def get_recommendations(
    workspace_id: str,
    request: RecommendationsRequest,
    authorization: str = Header(None),
):
    """Get AI recommendations for the workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    recs = workspace_manager.get_recommendations(
        workspace_id,
        user_id=user_id,
        context=request.context or "",
        max_recommendations=request.max_recommendations or 10,
    )
    return {
        "status": "OK",
        "recommendations": [
            {
                "id": r.id,
                "type": r.type,
                "title": r.title,
                "description": r.description,
                "confidence": r.confidence,
                "target_id": r.target_id,
                "metadata": r.metadata,
            }
            for r in recs
        ],
    }


@router.get("/{workspace_id}/dashboard")
async def get_workspace_dashboard(workspace_id: str, authorization: str = Header(None)):
    """Get the workspace dashboard with analytics and widgets."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    dashboard = workspace_manager.get_workspace_dashboard(workspace_id)
    if not dashboard:
        dashboard = workspace_manager.create_dashboard(
            workspace_id=workspace_id,
            owner_id=user_id,
            name="Default",
            is_default=True,
        )

    projects = workspace_manager.list_projects(workspace_id)
    tasks = workspace_manager.list_tasks(workspace_id)
    notes = workspace_manager.list_notes(workspace_id)

    open_tasks = [t for t in tasks if t.status not in ("done",)]
    done_tasks = [t for t in tasks if t.status == "done"]

    return {
        "status": "OK",
        "dashboard": {
            "id": dashboard.id,
            "name": dashboard.name,
            "widgets": [
                {
                    "id": w.id,
                    "type": w.type,
                    "title": w.title,
                    "config": w.config,
                    "position": w.position,
                    "size": w.size,
                }
                for w in dashboard.widgets
            ],
            "layout": dashboard.layout,
            "updated_at": dashboard.updated_at,
        },
        "overview": {
            "projects_total": len(projects),
            "projects_active": sum(1 for p in projects if p.status == "active"),
            "notes_total": len(notes),
            "tasks_total": len(tasks),
            "tasks_open": len(open_tasks),
            "tasks_done": len(done_tasks),
            "completion_rate": (len(done_tasks) / len(tasks)) if tasks else 0.0,
        },
    }


@router.post("/{workspace_id}/dashboard/widgets")
async def add_widget(
    workspace_id: str,
    request: AddWidgetRequest,
    authorization: str = Header(None),
):
    """Add a widget to the workspace dashboard."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    dashboard = workspace_manager.get_workspace_dashboard(workspace_id)
    if not dashboard:
        dashboard = workspace_manager.create_dashboard(
            workspace_id=workspace_id,
            owner_id=user_id,
            name="Default",
            is_default=True,
        )

    widget = workspace_manager.add_widget(
        dashboard.id,
        widget_type=request.widget_type,
        title=request.title,
        config=request.config,
    )
    if not widget:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to add widget")

    return {"status": "OK", "widget_id": widget.id}


# ============================================================================
# Files & Threads
# ============================================================================

@router.post("/{workspace_id}/files")
async def add_file(workspace_id: str, request: CreateFileRequest, authorization: str = Header(None)):
    """Register a shared file in the workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    file = workspace_manager.add_file(
        workspace_id=workspace_id,
        name=request.name,
        uploaded_by=user_id,
        url=request.url or "",
        size_bytes=request.size_bytes or 0,
        content_type=request.content_type or "",
        description=request.description or "",
    )
    if not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to register file")

    return {
        "status": "OK",
        "file": {
            "id": file.id,
            "name": file.name,
            "url": file.url,
            "size_bytes": file.size_bytes,
            "content_type": file.content_type,
            "uploaded_by": file.uploaded_by,
            "created_at": file.created_at,
        },
    }


@router.get("/{workspace_id}/files")
async def list_files(workspace_id: str, authorization: str = Header(None)):
    """List shared files in the workspace."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_read(user_id, workspace_id)

    files = workspace_manager.list_files(workspace_id)
    return {
        "status": "OK",
        "files": [
            {
                "id": f.id,
                "name": f.name,
                "url": f.url,
                "size_bytes": f.size_bytes,
                "content_type": f.content_type,
                "uploaded_by": f.uploaded_by,
                "created_at": f.created_at,
            }
            for f in files
        ],
    }


@router.post("/{workspace_id}/threads")
async def create_thread(workspace_id: str, request: CreateThreadRequest, authorization: str = Header(None)):
    """Open a discussion thread on a workspace resource."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    thread = workspace_manager.create_thread(
        workspace_id=workspace_id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        user_id=user_id,
        title=request.title or "",
        initial_message=request.initial_message or "",
    )
    if not thread:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create thread")

    return {
        "status": "OK",
        "thread": {
            "id": thread.id,
            "resource_type": thread.resource_type,
            "resource_id": thread.resource_id,
            "title": thread.title,
            "created_at": thread.created_at,
        },
    }


@router.post("/{workspace_id}/threads/{thread_id}/reply")
async def reply_to_thread(
    workspace_id: str,
    thread_id: str,
    request: ThreadReplyRequest,
    authorization: str = Header(None),
):
    """Reply to a discussion thread."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    message = workspace_manager.reply_to_thread(thread_id, user_id, request.content)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    return {"status": "OK", "message": message}


@router.post("/{workspace_id}/threads/{thread_id}/resolve")
async def resolve_thread(workspace_id: str, thread_id: str, authorization: str = Header(None)):
    """Mark a discussion thread as resolved."""
    user_id = get_user_id_from_token(authorization)
    _require_workspace_write(user_id, workspace_id)

    if not workspace_manager.resolve_thread(thread_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    return {"status": "OK", "message": "Thread resolved"}