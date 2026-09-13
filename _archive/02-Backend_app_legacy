"""Workspace data types — projects, notes, tasks, memory, dashboards, recommendations.

Stage 21 Step 3 — Intelligent Workspace data models.
"""

from __future__ import annotations

import time
import secrets
from dataclasses import dataclass, field
from typing import Optional


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
    status: str = "active"
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
    status: str = "todo"
    priority: str = "medium"
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
    category: str = "general"
    importance: float = 0.5
    source: str = ""
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
    type: str
    title: str
    config: dict = field(default_factory=dict)
    position: int = 0
    size: str = "medium"


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
    type: str
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
    resource_type: str
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
