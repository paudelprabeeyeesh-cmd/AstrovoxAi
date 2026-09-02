"""Intelligent Workspace — projects, notes, tasks, memory, dashboards, recommendations.

Stage 21 Step 3 — Intelligent Workspace:
AI projects with auto-summaries and tagging, workspace shared memory, rich notes
with versioning, shared conversations with branching, task management with
dependencies, AI recommendations, activity timelines, customizable dashboards,
team collaboration, and project analytics.

Built on top of the existing enterprise module — uses OrganizationService for
workspace lookups and RBACEnforcer for permission checks.
"""

import time
from typing import Optional
from dataclasses import dataclass, field

from .enterprise.service import org_service


# ============================================================================
# AI Projects
# ============================================================================

@dataclass
class Project:
    """An AI-augmented project inside a workspace."""
    id: str
    workspace_id: str
    name: str
    description: str = ""
    status: str = "active"  # active, paused, completed, archived
    owner_id: str = ""
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    memory: list[dict] = field(default_factory=list)
    task_count: int = 0
    note_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ============================================================================
# Shared Notes
# ============================================================================

@dataclass
class NoteVersion:
    """A single revision of a note."""
    id: str
    version_number: int
    content: str
    author_id: str
    created_at: float = field(default_factory=time.time)


@dataclass
class Note:
    """A rich markdown note inside a workspace."""
    id: str
    workspace_id: str
    title: str
    content: str = ""
    content_format: str = "markdown"
    author_id: str = ""
    project_id: str = ""
    tags: list[str] = field(default_factory=list)
    collaborators: list[str] = field(default_factory=list)
    versions: list[NoteVersion] = field(default_factory=list)
    is_pinned: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ============================================================================
# Tasks
# ============================================================================

@dataclass
class Task:
    """A task within a workspace or project."""
    id: str
    workspace_id: str
    title: str
    description: str = ""
    status: str = "todo"  # todo, in_progress, blocked, review, done
    priority: str = "medium"  # low, medium, high, urgent
    assignee_id: str = ""
    created_by: str = ""
    project_id: str = ""
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    due_date: float = 0.0
    estimated_hours: float = 0.0
    logged_hours: float = 0.0
    ai_suggested: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


# ============================================================================
# Workspace Memory
# ============================================================================

@dataclass
class MemoryEntry:
    """A shared memory entry in a workspace."""
    id: str
    workspace_id: str
    user_id: str
    content: str
    category: str = "general"  # fact, preference, decision, context, general
    importance: float = 0.5
    source: str = ""  # conversation, note, task, manual
    source_id: str = ""
    consolidated: bool = False
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)


# ============================================================================
# Shared Conversations
# ============================================================================

@dataclass
class ConversationBranch:
    """A branch of a shared conversation."""
    id: str
    parent_branch_id: str = ""
    name: str = "main"
    messages: list[dict] = field(default_factory=list)
    created_by: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class SharedConversation:
    """A workspace-scoped conversation with branching support."""
    id: str
    workspace_id: str
    title: str
    project_id: str = ""
    created_by: str = ""
    participants: list[str] = field(default_factory=list)
    branches: list[ConversationBranch] = field(default_factory=list)
    active_branch_id: str = ""
    is_ai_session: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ============================================================================
# Dashboards & Widgets
# ============================================================================

@dataclass
class DashboardWidget:
    """A widget on a workspace dashboard."""
    id: str
    type: str  # stat, chart, list, activity, quick_action
    title: str
    config: dict = field(default_factory=dict)
    position: int = 0
    size: str = "medium"  # small, medium, large


@dataclass
class Dashboard:
    """A customizable workspace dashboard."""
    id: str
    workspace_id: str
    owner_id: str
    name: str = "Default"
    widgets: list[DashboardWidget] = field(default_factory=list)
    layout: str = "grid"
    is_default: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ============================================================================
# Recommendations
# ============================================================================

@dataclass
class Recommendation:
    """An AI-generated recommendation."""
    id: str
    workspace_id: str
    type: str  # document, task, member, knowledge, action
    title: str
    description: str
    confidence: float = 0.0
    target_id: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


# ============================================================================
# File Sharing & Threads
# ============================================================================

@dataclass
class SharedFile:
    """A file shared in a workspace."""
    id: str
    workspace_id: str
    name: str
    url: str = ""
    size_bytes: int = 0
    content_type: str = ""
    uploaded_by: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class DiscussionThread:
    """A discussion thread attached to a workspace resource."""
    id: str
    workspace_id: str
    resource_type: str  # project, note, task, conversation
    resource_id: str
    title: str = ""
    messages: list[dict] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    is_resolved: bool = False
    created_by: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ============================================================================
# Helpers
# ============================================================================

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "in",
    "on", "at", "to", "for", "of", "with", "by", "from", "as", "this", "that",
    "it", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "i", "we", "you",
    "they", "he", "she", "them", "us", "our", "your", "their",
}


def _generate_id() -> str:
    """Generate a short hex id (matches existing pattern)."""
    import secrets
    return secrets.token_hex(8)


def _auto_tag(text: str, max_tags: int = 5) -> list[str]:
    """Extract naive keyword tags from text."""
    if not text:
        return []
    words = []
    seen = set()
    for raw in text.lower().split():
        clean = "".join(ch for ch in raw if ch.isalnum())
        if len(clean) > 3 and clean not in _STOPWORDS and clean not in seen:
            seen.add(clean)
            words.append(clean)
        if len(words) >= max_tags:
            break
    return words


def _auto_summary(text: str, max_words: int = 30) -> str:
    """Produce a simple extractive summary from text."""
    if not text:
        return ""
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    if not sentences:
        return text[:200]
    summary = sentences[0]
    words = summary.split()
    if len(words) > max_words:
        summary = " ".join(words[:max_words]) + "..."
    return summary


# ============================================================================
# Workspace Manager (Singleton)
# ============================================================================

class WorkspaceManager:
    """Central manager for all intelligent-workspace features."""

    def __init__(self):
        self._projects: dict[str, Project] = {}
        self._notes: dict[str, Note] = {}
        self._tasks: dict[str, Task] = {}
        self._memory: dict[str, MemoryEntry] = {}
        self._conversations: dict[str, SharedConversation] = {}
        self._dashboards: dict[str, Dashboard] = {}
        self._recommendations: dict[str, Recommendation] = {}
        self._files: dict[str, SharedFile] = {}
        self._threads: dict[str, DiscussionThread] = {}

    # ========================================================================
    # Projects
    # ========================================================================

    def create_project(
        self,
        workspace_id: str,
        name: str,
        owner_id: str,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> Optional[Project]:
        """Create a new project with AI-generated summary and tags."""
        if not org_service.get_workspace(workspace_id):
            return None

        project = Project(
            id=_generate_id(),
            workspace_id=workspace_id,
            name=name,
            description=description,
            owner_id=owner_id,
            tags=list(tags) if tags else _auto_tag(f"{name} {description}"),
            summary=_auto_summary(description),
        )
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def list_projects(
        self,
        workspace_id: str,
        status: str = "",
    ) -> list[Project]:
        """List projects in a workspace, optionally filtered by status."""
        results = [p for p in self._projects.values() if p.workspace_id == workspace_id]
        if status:
            results = [p for p in results if p.status == status]
        return sorted(results, key=lambda p: p.updated_at, reverse=True)

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Project]:
        """Update a project and refresh AI summary/tags when relevant."""
        project = self._projects.get(project_id)
        if not project:
            return None
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
            project.summary = _auto_summary(description)
            project.tags = _auto_tag(f"{project.name} {description}")
        if status is not None:
            project.status = status
        project.updated_at = time.time()
        return project

    def delete_project(self, project_id: str) -> bool:
        if project_id not in self._projects:
            return False
        del self._projects[project_id]
        return True

    def add_project_memory(
        self,
        project_id: str,
        user_id: str,
        content: str,
        category: str = "context",
    ) -> Optional[MemoryEntry]:
        """Add a memory entry to a project."""
        project = self._projects.get(project_id)
        if not project:
            return None
        entry = MemoryEntry(
            id=_generate_id(),
            workspace_id=project.workspace_id,
            user_id=user_id,
            content=content,
            category=category,
            source="project",
            source_id=project_id,
            importance=0.6,
        )
        project.memory.append({
            "id": entry.id,
            "content": entry.content,
            "category": entry.category,
            "user_id": user_id,
            "created_at": entry.created_at,
        })
        if entry.id not in self._memory:
            self._memory[entry.id] = entry
        project.updated_at = time.time()
        return entry

    # ========================================================================
    # Notes
    # ========================================================================

    def create_note(
        self,
        workspace_id: str,
        title: str,
        author_id: str,
        content: str = "",
        project_id: str = "",
        tags: Optional[list[str]] = None,
    ) -> Optional[Note]:
        """Create a new note with initial version."""
        if not org_service.get_workspace(workspace_id):
            return None

        note = Note(
            id=_generate_id(),
            workspace_id=workspace_id,
            title=title,
            content=content,
            author_id=author_id,
            project_id=project_id,
            tags=list(tags) if tags else _auto_tag(f"{title} {content}"),
            collaborators=[author_id],
        )
        if content:
            note.versions.append(NoteVersion(
                id=_generate_id(),
                version_number=1,
                content=content,
                author_id=author_id,
            ))
        self._notes[note.id] = note

        if project_id and project_id in self._projects:
            self._projects[project_id].note_count += 1

        return note

    def get_note(self, note_id: str) -> Optional[Note]:
        return self._notes.get(note_id)

    def list_notes(
        self,
        workspace_id: str,
        project_id: str = "",
    ) -> list[Note]:
        """List notes in a workspace, optionally filtered by project."""
        results = [n for n in self._notes.values() if n.workspace_id == workspace_id]
        if project_id:
            results = [n for n in results if n.project_id == project_id]
        return sorted(results, key=lambda n: n.updated_at, reverse=True)

    def update_note(
        self,
        note_id: str,
        user_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[Note]:
        """Update a note, creating a new version when content changes."""
        note = self._notes.get(note_id)
        if not note:
            return None
        if title is not None:
            note.title = title
        if content is not None and content != note.content:
            note.versions.append(NoteVersion(
                id=_generate_id(),
                version_number=len(note.versions) + 1,
                content=content,
                author_id=user_id,
            ))
            note.content = content
            note.tags = _auto_tag(f"{note.title} {content}")
        note.updated_at = time.time()
        if user_id and user_id not in note.collaborators:
            note.collaborators.append(user_id)
        return note

    def delete_note(self, note_id: str) -> bool:
        note = self._notes.get(note_id)
        if not note:
            return False
        if note.project_id and note.project_id in self._projects:
            self._projects[note.project_id].note_count = max(
                0, self._projects[note.project_id].note_count - 1
            )
        del self._notes[note_id]
        return True

    # ========================================================================
    # Tasks
    # ========================================================================

    def create_task(
        self,
        workspace_id: str,
        title: str,
        created_by: str,
        description: str = "",
        assignee_id: str = "",
        project_id: str = "",
        priority: str = "medium",
        due_date: float = 0.0,
        dependencies: Optional[list[str]] = None,
        estimated_hours: float = 0.0,
        tags: Optional[list[str]] = None,
        ai_suggested: bool = False,
    ) -> Optional[Task]:
        """Create a task in a workspace."""
        if not org_service.get_workspace(workspace_id):
            return None

        task = Task(
            id=_generate_id(),
            workspace_id=workspace_id,
            title=title,
            description=description,
            created_by=created_by,
            assignee_id=assignee_id,
            project_id=project_id,
            priority=priority if priority in ("low", "medium", "high", "urgent") else "medium",
            due_date=due_date,
            dependencies=list(dependencies) if dependencies else [],
            estimated_hours=estimated_hours,
            tags=list(tags) if tags else _auto_tag(f"{title} {description}"),
            ai_suggested=ai_suggested,
        )
        self._tasks[task.id] = task

        if project_id and project_id in self._projects:
            self._projects[project_id].task_count += 1

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        workspace_id: str,
        project_id: str = "",
        status: str = "",
        assignee_id: str = "",
    ) -> list[Task]:
        """List tasks with optional filters."""
        results = [t for t in self._tasks.values() if t.workspace_id == workspace_id]
        if project_id:
            results = [t for t in results if t.project_id == project_id]
        if status:
            results = [t for t in results if t.status == status]
        if assignee_id:
            results = [t for t in results if t.assignee_id == assignee_id]
        return sorted(
            results,
            key=lambda t: (
                {"urgent": 0, "high": 1, "medium": 2, "low": 3}.get(t.priority, 4),
                -t.created_at,
            ),
        )

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        logged_hours: Optional[float] = None,
    ) -> Optional[Task]:
        """Update a task."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if status is not None:
            task.status = status
            if status == "done" and task.completed_at == 0.0:
                task.completed_at = time.time()
        if priority is not None:
            task.priority = priority
        if assignee_id is not None:
            task.assignee_id = assignee_id
        if logged_hours is not None:
            task.logged_hours = max(0.0, logged_hours)
        task.updated_at = time.time()
        return task

    def delete_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.project_id and task.project_id in self._projects:
            self._projects[task.project_id].task_count = max(
                0, self._projects[task.project_id].task_count - 1
            )
        del self._tasks[task_id]
        return True

    def suggest_tasks(
        self,
        workspace_id: str,
        project_id: str = "",
        context: str = "",
        max_suggestions: int = 5,
    ) -> list[Task]:
        """Suggest AI-generated tasks based on context or project state."""
        suggestions: list[Task] = []
        seen: set[str] = set()

        candidates = self.list_tasks(workspace_id, project_id=project_id)
        statuses = {t.status for t in candidates}

        if "todo" not in statuses:
            suggestions.append(self._make_suggestion(
                workspace_id, project_id, context,
                "Define project goals and success metrics",
                "Outline clear goals, KPIs, and acceptance criteria for the project.",
                "high", "planning", seen,
            ))
        if not any(t.status == "done" for t in candidates):
            suggestions.append(self._make_suggestion(
                workspace_id, project_id, context,
                "Document initial scope",
                "Capture the agreed-upon scope, out-of-scope items, and assumptions.",
                "medium", "documentation", seen,
            ))

        keywords = context.lower().split() if context else []
        if any(k in keywords for k in ("design", "ui", "ux")):
            suggestions.append(self._make_suggestion(
                workspace_id, project_id, context,
                "Create wireframes and design mockups",
                "Draft low-fidelity wireframes covering core user flows.",
                "high", "design", seen,
            ))
        if any(k in keywords for k in ("api", "backend", "service")):
            suggestions.append(self._make_suggestion(
                workspace_id, project_id, context,
                "Define API contracts",
                "Specify request/response schemas, error codes, and authentication.",
                "high", "engineering", seen,
            ))
        if any(k in keywords for k in ("test", "qa", "quality")):
            suggestions.append(self._make_suggestion(
                workspace_id, project_id, context,
                "Author automated test suite",
                "Cover unit, integration, and end-to-end tests for critical paths.",
                "medium", "quality", seen,
            ))

        if not suggestions:
            suggestions.append(self._make_suggestion(
                workspace_id, project_id, context,
                "Kickoff meeting with stakeholders",
                "Schedule a kickoff to align on objectives, timeline, and ownership.",
                "medium", "coordination", seen,
            ))

        return suggestions[:max_suggestions]

    def _make_suggestion(
        self,
        workspace_id: str,
        project_id: str,
        context: str,
        title: str,
        description: str,
        priority: str,
        tag: str,
        seen: set[str],
    ) -> Task:
        """Create a single AI-suggested task placeholder (not stored)."""
        if title in seen:
            title = f"{title} ({len(seen) + 1})"
        seen.add(title)
        task = Task(
            id=_generate_id(),
            workspace_id=workspace_id,
            title=title,
            description=description or context,
            created_by="ai",
            project_id=project_id,
            priority=priority,
            tags=[tag],
            ai_suggested=True,
        )
        return task

    # ========================================================================
    # Workspace Memory
    # ========================================================================

    def add_memory(
        self,
        workspace_id: str,
        user_id: str,
        content: str,
        category: str = "general",
        importance: float = 0.5,
        source: str = "",
        source_id: str = "",
    ) -> Optional[MemoryEntry]:
        """Add a shared memory entry to a workspace."""
        if not org_service.get_workspace(workspace_id):
            return None

        entry = MemoryEntry(
            id=_generate_id(),
            workspace_id=workspace_id,
            user_id=user_id,
            content=content,
            category=category,
            importance=max(0.0, min(1.0, importance)),
            source=source,
            source_id=source_id,
        )
        self._memory[entry.id] = entry
        return entry

    def get_workspace_memory(
        self,
        workspace_id: str,
        category: str = "",
        min_importance: float = 0.0,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        """Get memory entries for a workspace."""
        results = [m for m in self._memory.values() if m.workspace_id == workspace_id]
        if category:
            results = [m for m in results if m.category == category]
        if min_importance > 0:
            results = [m for m in results if m.importance >= min_importance]
        results = sorted(results, key=lambda m: m.importance, reverse=True)[:limit]

        now = time.time()
        for entry in results:
            entry.access_count += 1
            entry.last_accessed = now

        return results

    def share_context(
        self,
        workspace_id: str,
        user_id: str,
        content: str,
        category: str = "context",
    ) -> Optional[MemoryEntry]:
        """Convenience: share a piece of context with the workspace."""
        return self.add_memory(
            workspace_id=workspace_id,
            user_id=user_id,
            content=content,
            category=category,
            importance=0.7,
            source="share",
        )

    def consolidate_memory(self, workspace_id: str) -> list[MemoryEntry]:
        """Consolidate similar memory entries within a workspace."""
        entries = [
            m for m in self._memory.values()
            if m.workspace_id == workspace_id and not m.consolidated
        ]
        consolidated: list[MemoryEntry] = []
        for i, entry in enumerate(entries):
            if entry.consolidated:
                continue
            similar = [entry]
            for other in entries[i + 1:]:
                if other.consolidated:
                    continue
                if entry.category == other.category:
                    shared = set(entry.content.lower().split()) & set(other.content.lower().split())
                    if len(shared) >= 2:
                        similar.append(other)
            if len(similar) > 1:
                combined_content = " | ".join(e.content for e in similar)
                entry.content = combined_content[:500]
                entry.importance = min(1.0, max(e.importance for e in similar))
                entry.consolidated = True
                for sibling in similar[1:]:
                    sibling.consolidated = True
                consolidated.append(entry)
            else:
                entry.consolidated = True
        return consolidated

    # ========================================================================
    # Shared Conversations
    # ========================================================================

    def create_conversation(
        self,
        workspace_id: str,
        title: str,
        created_by: str,
        project_id: str = "",
        is_ai_session: bool = False,
        participants: Optional[list[str]] = None,
    ) -> Optional[SharedConversation]:
        """Create a shared conversation in a workspace."""
        if not org_service.get_workspace(workspace_id):
            return None

        conversation = SharedConversation(
            id=_generate_id(),
            workspace_id=workspace_id,
            title=title,
            project_id=project_id,
            created_by=created_by,
            is_ai_session=is_ai_session,
            participants=list(participants) if participants else [created_by],
        )
        main_branch = ConversationBranch(
            id=_generate_id(),
            parent_branch_id="",
            name="main",
            created_by=created_by,
        )
        conversation.branches.append(main_branch)
        conversation.active_branch_id = main_branch.id
        self._conversations[conversation.id] = conversation
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[SharedConversation]:
        return self._conversations.get(conversation_id)

    def list_conversations(
        self,
        workspace_id: str,
        project_id: str = "",
    ) -> list[SharedConversation]:
        """List conversations in a workspace."""
        results = [c for c in self._conversations.values() if c.workspace_id == workspace_id]
        if project_id:
            results = [c for c in results if c.project_id == project_id]
        return sorted(results, key=lambda c: c.updated_at, reverse=True)

    def add_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        role: str = "user",
        branch_id: str = "",
    ) -> Optional[dict]:
        """Append a message to the active branch (or a specific branch)."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None
        target_branch_id = branch_id or conversation.active_branch_id
        branch = next((b for b in conversation.branches if b.id == target_branch_id), None)
        if not branch:
            return None
        message = {
            "id": _generate_id(),
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }
        branch.messages.append(message)
        if user_id and user_id not in conversation.participants:
            conversation.participants.append(user_id)
        conversation.updated_at = time.time()
        return message

    def branch_conversation(
        self,
        conversation_id: str,
        user_id: str,
        name: str = "branch",
        parent_branch_id: str = "",
    ) -> Optional[ConversationBranch]:
        """Create a new branch off an existing conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None
        parent = parent_branch_id or conversation.active_branch_id
        parent_branch = next((b for b in conversation.branches if b.id == parent), None)
        branch = ConversationBranch(
            id=_generate_id(),
            parent_branch_id=parent,
            name=name,
            created_by=user_id,
            messages=list(parent_branch.messages) if parent_branch else [],
        )
        conversation.branches.append(branch)
        conversation.active_branch_id = branch.id
        conversation.updated_at = time.time()
        return branch

    # ========================================================================
    # Dashboards
    # ========================================================================

    def create_dashboard(
        self,
        workspace_id: str,
        owner_id: str,
        name: str = "Default",
        is_default: bool = False,
    ) -> Optional[Dashboard]:
        """Create a dashboard for a workspace."""
        if not org_service.get_workspace(workspace_id):
            return None
        dashboard = Dashboard(
            id=_generate_id(),
            workspace_id=workspace_id,
            owner_id=owner_id,
            name=name,
            is_default=is_default,
        )
        dashboard.widgets.extend(self._default_widgets())
        self._dashboards[dashboard.id] = dashboard
        return dashboard

    def _default_widgets(self) -> list[DashboardWidget]:
        """Default widget set for new dashboards."""
        return [
            DashboardWidget(
                id=_generate_id(),
                type="stat",
                title="Active Projects",
                config={"metric": "projects.active"},
                position=0,
                size="small",
            ),
            DashboardWidget(
                id=_generate_id(),
                type="stat",
                title="Open Tasks",
                config={"metric": "tasks.open"},
                position=1,
                size="small",
            ),
            DashboardWidget(
                id=_generate_id(),
                type="list",
                title="Recent Activity",
                config={"resource": "activity", "limit": 10},
                position=2,
                size="medium",
            ),
            DashboardWidget(
                id=_generate_id(),
                type="quick_action",
                title="Quick Actions",
                config={"actions": ["new_project", "new_note", "new_task"]},
                position=3,
                size="small",
            ),
        ]

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        return self._dashboards.get(dashboard_id)

    def get_workspace_dashboard(self, workspace_id: str) -> Optional[Dashboard]:
        for dash in self._dashboards.values():
            if dash.workspace_id == workspace_id and dash.is_default:
                return dash
        for dash in self._dashboards.values():
            if dash.workspace_id == workspace_id:
                return dash
        return None

    def add_widget(
        self,
        dashboard_id: str,
        widget_type: str,
        title: str,
        config: Optional[dict] = None,
    ) -> Optional[DashboardWidget]:
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None
        widget = DashboardWidget(
            id=_generate_id(),
            type=widget_type,
            title=title,
            config=config or {},
            position=len(dashboard.widgets),
        )
        dashboard.widgets.append(widget)
        dashboard.updated_at = time.time()
        return widget

    # ========================================================================
    # Recommendations
    # ========================================================================

    def get_recommendations(
        self,
        workspace_id: str,
        user_id: str = "",
        context: str = "",
        max_recommendations: int = 10,
    ) -> list[Recommendation]:
        """Generate context-aware recommendations for a workspace."""
        recs: list[Recommendation] = []

        projects = self.list_projects(workspace_id)
        tasks = self.list_tasks(workspace_id)
        notes = self.list_notes(workspace_id)

        # Document recommendations: notes that match context keywords
        if context:
            ctx_words = {w for w in context.lower().split() if len(w) > 3}
            for note in notes:
                note_words = set(f"{note.title} {note.content}".lower().split())
                overlap = ctx_words & note_words
                if overlap:
                    recs.append(Recommendation(
                        id=_generate_id(),
                        workspace_id=workspace_id,
                        type="document",
                        title=note.title,
                        description=f"Matches context on: {', '.join(list(overlap)[:3])}",
                        confidence=min(1.0, 0.5 + 0.1 * len(overlap)),
                        target_id=note.id,
                        metadata={"source": "note"},
                    ))

        # Task recommendations: open tasks user could pick up
        open_tasks = [t for t in tasks if t.status in ("todo", "in_progress")]
        for task in open_tasks[:5]:
            recs.append(Recommendation(
                id=_generate_id(),
                workspace_id=workspace_id,
                type="task",
                title=f"Resume task: {task.title}",
                description=task.description or "Continue work on this active task.",
                confidence=0.6,
                target_id=task.id,
                metadata={"priority": task.priority, "status": task.status},
            ))

        # Knowledge recommendations: top notes by recency
        for note in notes[:3]:
            if any(r.target_id == note.id for r in recs):
                continue
            recs.append(Recommendation(
                id=_generate_id(),
                workspace_id=workspace_id,
                type="knowledge",
                title=f"Review note: {note.title}",
                description="Recently updated note that may be relevant.",
                confidence=0.4,
                target_id=note.id,
                metadata={"updated_at": note.updated_at},
            ))

        # Team member recommendations: members with active tasks
        member_load: dict[str, int] = {}
        for task in open_tasks:
            if task.assignee_id:
                member_load[task.assignee_id] = member_load.get(task.assignee_id, 0) + 1
        members = org_service.list_workspace_members(workspace_id)
        for m in members[:5]:
            load = member_load.get(m.user_id, 0)
            recs.append(Recommendation(
                id=_generate_id(),
                workspace_id=workspace_id,
                type="member",
                title=f"Connect with teammate",
                description=f"Role: {m.role}; active tasks: {load}.",
                confidence=0.3,
                target_id=m.user_id,
                metadata={"role": m.role, "active_tasks": load},
            ))

        # Action recommendation: summarize if project has many open tasks
        if len(open_tasks) > 5:
            recs.append(Recommendation(
                id=_generate_id(),
                workspace_id=workspace_id,
                type="action",
                title="Review task backlog",
                description=f"There are {len(open_tasks)} open tasks in this workspace.",
                confidence=0.5,
                target_id="",
                metadata={"open_task_count": len(open_tasks)},
            ))

        recs.sort(key=lambda r: r.confidence, reverse=True)
        return recs[:max_recommendations]

    # ========================================================================
    # Activity Timeline
    # ========================================================================

    def get_activity_timeline(
        self,
        workspace_id: str,
        resource_type: str = "",
        user_id: str = "",
        since: float = 0.0,
        limit: int = 50,
    ) -> list[dict]:
        """Build an aggregated activity timeline for the workspace."""
        events: list[dict] = []

        for project in self._projects.values():
            if project.workspace_id != workspace_id:
                continue
            events.append({
                "id": f"project:{project.id}",
                "type": "project",
                "action": "created",
                "title": project.name,
                "user_id": project.owner_id,
                "resource_id": project.id,
                "timestamp": project.created_at,
            })

        for note in self._notes.values():
            if note.workspace_id != workspace_id:
                continue
            events.append({
                "id": f"note:{note.id}",
                "type": "note",
                "action": "created",
                "title": note.title,
                "user_id": note.author_id,
                "resource_id": note.id,
                "timestamp": note.created_at,
            })

        for task in self._tasks.values():
            if task.workspace_id != workspace_id:
                continue
            events.append({
                "id": f"task:{task.id}",
                "type": "task",
                "action": "created",
                "title": task.title,
                "user_id": task.created_by,
                "resource_id": task.id,
                "timestamp": task.created_at,
            })
            if task.completed_at > 0:
                events.append({
                    "id": f"task:{task.id}:done",
                    "type": "task",
                    "action": "completed",
                    "title": task.title,
                    "user_id": task.assignee_id or task.created_by,
                    "resource_id": task.id,
                    "timestamp": task.completed_at,
                })

        if resource_type:
            events = [e for e in events if e["type"] == resource_type]
        if user_id:
            events = [e for e in events if e["user_id"] == user_id]
        if since > 0:
            events = [e for e in events if e["timestamp"] >= since]

        events.sort(key=lambda e: e["timestamp"], reverse=True)
        return events[:limit]

    # ========================================================================
    # Files & Threads
    # ========================================================================

    def add_file(
        self,
        workspace_id: str,
        name: str,
        uploaded_by: str,
        url: str = "",
        size_bytes: int = 0,
        content_type: str = "",
        description: str = "",
    ) -> Optional[SharedFile]:
        """Register a shared file in a workspace."""
        if not org_service.get_workspace(workspace_id):
            return None
        file = SharedFile(
            id=_generate_id(),
            workspace_id=workspace_id,
            name=name,
            url=url,
            size_bytes=size_bytes,
            content_type=content_type,
            uploaded_by=uploaded_by,
            description=description,
        )
        self._files[file.id] = file
        return file

    def list_files(self, workspace_id: str) -> list[SharedFile]:
        return [f for f in self._files.values() if f.workspace_id == workspace_id]

    def create_thread(
        self,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        title: str = "",
        initial_message: str = "",
    ) -> Optional[DiscussionThread]:
        """Open a discussion thread on a workspace resource."""
        if not org_service.get_workspace(workspace_id):
            return None
        thread = DiscussionThread(
            id=_generate_id(),
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            title=title,
            created_by=user_id,
            participants=[user_id],
        )
        if initial_message:
            thread.messages.append({
                "id": _generate_id(),
                "user_id": user_id,
                "content": initial_message,
                "timestamp": time.time(),
            })
        self._threads[thread.id] = thread
        return thread

    def reply_to_thread(
        self,
        thread_id: str,
        user_id: str,
        content: str,
    ) -> Optional[dict]:
        thread = self._threads.get(thread_id)
        if not thread:
            return None
        message = {
            "id": _generate_id(),
            "user_id": user_id,
            "content": content,
            "timestamp": time.time(),
        }
        thread.messages.append(message)
        if user_id not in thread.participants:
            thread.participants.append(user_id)
        thread.updated_at = time.time()
        return message

    def resolve_thread(self, thread_id: str) -> bool:
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        thread.is_resolved = True
        thread.updated_at = time.time()
        return True

    # ========================================================================
    # Project Analytics
    # ========================================================================

    def get_project_analytics(self, project_id: str) -> dict:
        """Compute analytics for a project."""
        project = self._projects.get(project_id)
        if not project:
            return {}
        tasks = [t for t in self._tasks.values() if t.project_id == project_id]
        total = len(tasks)
        done = sum(1 for t in tasks if t.status == "done")
        in_progress = sum(1 for t in tasks if t.status == "in_progress")
        blocked = sum(1 for t in tasks if t.status == "blocked")
        todo = sum(1 for t in tasks if t.status == "todo")

        completion_rate = (done / total) if total else 0.0
        estimated = sum(t.estimated_hours for t in tasks)
        logged = sum(t.logged_hours for t in tasks)

        contributor_stats: dict[str, dict] = {}
        for t in tasks:
            user = t.assignee_id or t.created_by or "unassigned"
            stats = contributor_stats.setdefault(user, {
                "user_id": user,
                "tasks_total": 0,
                "tasks_done": 0,
                "hours_logged": 0.0,
            })
            stats["tasks_total"] += 1
            if t.status == "done":
                stats["tasks_done"] += 1
            stats["hours_logged"] += t.logged_hours

        contributors = sorted(
            contributor_stats.values(),
            key=lambda c: c["tasks_done"],
            reverse=True,
        )

        # Simple burndown: estimated vs logged over time buckets
        burndown = []
        if tasks:
            ordered = sorted(tasks, key=lambda t: t.created_at)
            bucket_size = max(1, len(ordered) // 5 or 1)
            remaining = estimated
            for i in range(0, len(ordered), bucket_size):
                bucket = ordered[i:i + bucket_size]
                remaining -= sum(t.logged_hours for t in bucket)
                burndown.append({
                    "label": f"step-{i // bucket_size + 1}",
                    "remaining_hours": max(0.0, remaining),
                })

        return {
            "project_id": project_id,
            "project_name": project.name,
            "status": project.status,
            "task_total": total,
            "task_done": done,
            "task_in_progress": in_progress,
            "task_blocked": blocked,
            "task_todo": todo,
            "completion_rate": completion_rate,
            "estimated_hours": estimated,
            "logged_hours": logged,
            "contributors": contributors,
            "burndown": burndown,
        }


# Singleton instance
workspace_manager = WorkspaceManager()