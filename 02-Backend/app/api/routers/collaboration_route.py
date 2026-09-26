"""Collaboration API — shared prompts, agents, documents, comments, version history."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel

from app.collaboration_platform import (
    ResourceType,
    CollaborationService,
)
from app.utils.auth.auth_utils import get_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])
service = CollaborationService()


# ============================================================================
# Request Models
# ============================================================================


class CreatePromptRequest(BaseModel):
    name: str
    content: str
    description: str = ""
    tags: Optional[list[str]] = None
    is_public: bool = False


class UpdatePromptRequest(BaseModel):
    content: str
    change_description: str = ""


class CreateAgentRequest(BaseModel):
    name: str
    role: str
    system_prompt: str
    model: str = "gpt-4"
    temperature: float = 0.7
    tools: Optional[list[str]] = None


class CreateDocumentRequest(BaseModel):
    title: str
    content: str = ""
    format: str = "markdown"


class UpdateDocumentRequest(BaseModel):
    content: str
    change_description: str = ""


class AddCommentRequest(BaseModel):
    resource_type: str
    resource_id: str
    content: str
    parent_id: Optional[str] = ""


class RecordVersionRequest(BaseModel):
    resource_type: str
    resource_id: str
    snapshot: str
    description: str = ""


class RestoreVersionRequest(BaseModel):
    resource_type: str
    resource_id: str
    version_id: str


# ============================================================================
# Shared Prompts
# ============================================================================


@router.post("/prompts")
async def create_prompt(
    workspace_id: str,
    request: CreatePromptRequest,
    authorization: str = Header(None),
):
    """Create a shared prompt in a workspace."""
    user_id = get_user_id_from_token(authorization)
    prompt = service.share_prompt(
        workspace_id=workspace_id,
        name=request.name,
        content=request.content,
        user_id=user_id,
        description=request.description,
        tags=request.tags,
        is_public=request.is_public,
    )
    return {
        "status": "OK",
        "prompt": {
            "id": prompt.id,
            "name": prompt.name,
            "version": prompt.version,
            "owner_id": prompt.owner_id,
            "is_public": prompt.is_public,
            "created_at": prompt.created_at,
        },
    }


@router.get("/prompts")
async def list_prompts(
    workspace_id: str,
    authorization: str = Header(None),
):
    """List shared prompts in a workspace."""
    get_user_id_from_token(authorization)
    prompts = service.prompts.list_workspace(workspace_id)
    return {
        "status": "OK",
        "prompts": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "version": p.version,
                "owner_id": p.owner_id,
                "tags": p.tags,
                "is_public": p.is_public,
                "updated_at": p.updated_at,
            }
            for p in prompts
        ],
    }


@router.get("/prompts/{prompt_id}")
async def get_prompt(prompt_id: str, authorization: str = Header(None)):
    """Get a shared prompt with version history."""
    get_user_id_from_token(authorization)
    prompt = service.prompts.get(prompt_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    versions = service.prompts.get_versions(prompt_id)
    return {
        "status": "OK",
        "prompt": {
            "id": prompt.id,
            "name": prompt.name,
            "content": prompt.content,
            "description": prompt.description,
            "version": prompt.version,
            "owner_id": prompt.owner_id,
            "tags": prompt.tags,
            "is_public": prompt.is_public,
            "versions": versions,
            "created_at": prompt.created_at,
            "updated_at": prompt.updated_at,
        },
    }


@router.patch("/prompts/{prompt_id}")
async def update_prompt(
    workspace_id: str,
    prompt_id: str,
    request: UpdatePromptRequest,
    authorization: str = Header(None),
):
    """Update a shared prompt."""
    user_id = get_user_id_from_token(authorization)
    prompt = service.prompts.update(prompt_id, user_id, request.content, request.change_description)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return {"status": "OK", "prompt_id": prompt.id, "version": prompt.version}


@router.post("/prompts/{prompt_id}/fork")
async def fork_prompt(
    workspace_id: str,
    prompt_id: str,
    new_name: str,
    authorization: str = Header(None),
):
    """Fork a shared prompt."""
    user_id = get_user_id_from_token(authorization)
    prompt = service.prompts.fork(prompt_id, user_id, new_name)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return {
        "status": "OK",
        "prompt": {
            "id": prompt.id,
            "name": prompt.name,
            "version": prompt.version,
            "owner_id": prompt.owner_id,
        },
    }


# ============================================================================
# Shared Agents
# ============================================================================


@router.post("/agents")
async def create_agent(
    workspace_id: str,
    request: CreateAgentRequest,
    authorization: str = Header(None),
):
    """Create a shared agent in a workspace."""
    user_id = get_user_id_from_token(authorization)
    agent = service.share_agent(
        workspace_id=workspace_id,
        name=request.name,
        role=request.role,
        system_prompt=request.system_prompt,
        user_id=user_id,
        model=request.model,
        temperature=request.temperature,
        tools=request.tools,
    )
    return {
        "status": "OK",
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "model": agent.model,
            "is_shared": agent.is_shared,
            "created_at": agent.created_at,
        },
    }


@router.get("/agents")
async def list_agents(
    workspace_id: str,
    authorization: str = Header(None),
):
    """List shared agents in a workspace."""
    get_user_id_from_token(authorization)
    agents = service.agents.list_workspace(workspace_id)
    return {
        "status": "OK",
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "role": a.role,
                "model": a.model,
                "temperature": a.temperature,
                "tools": a.tools,
                "is_shared": a.is_shared,
                "owner_id": a.owner_id,
                "updated_at": a.updated_at,
            }
            for a in agents
        ],
    }


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, authorization: str = Header(None)):
    """Get a shared agent."""
    get_user_id_from_token(authorization)
    agent = service.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return {
        "status": "OK",
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "system_prompt": agent.system_prompt,
            "model": agent.model,
            "temperature": agent.temperature,
            "tools": agent.tools,
            "is_shared": agent.is_shared,
            "metadata": agent.metadata,
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
        },
    }


@router.post("/agents/{agent_id}/share")
async def share_agent(agent_id: str, authorization: str = Header(None)):
    """Share an agent with the workspace."""
    user_id = get_user_id_from_token(authorization)
    if not service.agents.share(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return {"status": "OK", "message": "Agent shared"}


@router.post("/agents/{agent_id}/unshare")
async def unshare_agent(agent_id: str, authorization: str = Header(None)):
    """Unshare an agent."""
    user_id = get_user_id_from_token(authorization)
    if not service.agents.unshare(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return {"status": "OK", "message": "Agent unshared"}


# ============================================================================
# Shared Documents
# ============================================================================


@router.post("/documents")
async def create_document(
    workspace_id: str,
    request: CreateDocumentRequest,
    authorization: str = Header(None),
):
    """Create a shared document."""
    user_id = get_user_id_from_token(authorization)
    doc = service.create_document(
        workspace_id=workspace_id,
        title=request.title,
        user_id=user_id,
        content=request.content,
        format=request.format,
    )
    return {
        "status": "OK",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "format": doc.format,
            "owner_id": doc.owner_id,
            "created_at": doc.created_at,
        },
    }


@router.get("/documents")
async def list_documents(
    workspace_id: str,
    authorization: str = Header(None),
):
    """List shared documents in a workspace."""
    get_user_id_from_token(authorization)
    docs = service.documents.list_workspace(workspace_id)
    return {
        "status": "OK",
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "format": d.format,
                "owner_id": d.owner_id,
                "is_locked": d.is_locked,
                "updated_at": d.updated_at,
            }
            for d in docs
        ],
    }


@router.get("/documents/{document_id}")
async def get_document(document_id: str, authorization: str = Header(None)):
    """Get a shared document with version history."""
    get_user_id_from_token(authorization)
    doc = service.documents.get(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    versions = service.documents.get_versions(document_id)
    return {
        "status": "OK",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "format": doc.format,
            "owner_id": doc.owner_id,
            "is_locked": doc.is_locked,
            "versions": versions,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        },
    }


@router.patch("/documents/{document_id}")
async def update_document(
    workspace_id: str,
    document_id: str,
    request: UpdateDocumentRequest,
    authorization: str = Header(None),
):
    """Update a shared document."""
    user_id = get_user_id_from_token(authorization)
    doc = service.documents.update(document_id, user_id, request.content, request.change_description)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {"status": "OK", "document_id": doc.id}


@router.post("/documents/{document_id}/restore")
async def restore_document_version(
    workspace_id: str,
    document_id: str,
    request: RestoreVersionRequest,
    authorization: str = Header(None),
):
    """Restore a document to a previous version."""
    user_id = get_user_id_from_token(authorization)
    doc = service.documents.restore_version(document_id, request.version_id, user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document or version not found")
    return {"status": "OK", "document_id": doc.id}


# ============================================================================
# Comments
# ============================================================================


@router.post("/comments")
async def add_comment(
    workspace_id: str,
    request: AddCommentRequest,
    authorization: str = Header(None),
):
    """Add a comment to a resource."""
    user_id = get_user_id_from_token(authorization)
    try:
        resource_type = ResourceType(request.resource_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resource type")

    comment = service.add_comment(
        resource_type=resource_type,
        resource_id=request.resource_id,
        author_id=user_id,
        content=request.content,
        parent_id=request.parent_id or "",
    )
    return {
        "status": "OK",
        "comment": {
            "id": comment.id,
            "author_id": comment.author_id,
            "content": comment.content,
            "created_at": comment.created_at,
            "parent_id": comment.parent_id,
            "mentions": comment.mentions,
        },
    }


@router.get("/comments")
async def list_comments(
    resource_type: str,
    resource_id: str,
    authorization: str = Header(None),
    include_resolved: bool = Query(default=True),
):
    """List comments for a resource."""
    get_user_id_from_token(authorization)
    try:
        rtype = ResourceType(resource_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resource type")

    comments = service.comments.get_for_resource(rtype, resource_id, include_resolved=include_resolved)
    return {
        "status": "OK",
        "comments": [
            {
                "id": c.id,
                "author_id": c.author_id,
                "content": c.content,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "parent_id": c.parent_id,
                "is_resolved": c.is_resolved,
                "mentions": c.mentions,
            }
            for c in comments
        ],
    }


@router.post("/comments/{comment_id}/resolve")
async def resolve_comment(comment_id: str, authorization: str = Header(None)):
    """Resolve a comment."""
    get_user_id_from_token(authorization)
    if not service.comments.resolve(comment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return {"status": "OK", "message": "Comment resolved"}


# ============================================================================
# Version History
# ============================================================================


@router.post("/versions")
async def record_version(
    workspace_id: str,
    request: RecordVersionRequest,
    authorization: str = Header(None),
):
    """Record a version for a resource."""
    user_id = get_user_id_from_token(authorization)
    try:
        resource_type = ResourceType(request.resource_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resource type")

    version = service.record_version(
        resource_type=resource_type,
        resource_id=request.resource_id,
        author_id=user_id,
        snapshot=request.snapshot,
        description=request.description,
    )
    return {
        "status": "OK",
        "version": {
            "id": version.id,
            "author_id": version.author_id,
            "description": version.description,
            "created_at": version.created_at,
        },
    }


@router.get("/versions")
async def get_version_history(
    resource_type: str,
    resource_id: str,
    authorization: str = Header(None),
    limit: int = Query(default=50, le=200),
):
    """Get version history for a resource."""
    get_user_id_from_token(authorization)
    try:
        rtype = ResourceType(resource_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resource type")

    history = service.versions.get_history(rtype, resource_id, limit=limit)
    return {"status": "OK", "versions": history, "count": len(history)}


# ============================================================================
# Live Collaboration State
# ============================================================================


@router.get("/live/{resource_type}/{resource_id}/state")
async def get_live_state(
    resource_type: str,
    resource_id: str,
    authorization: str = Header(None),
):
    """Get live collaboration state for a resource."""
    get_user_id_from_token(authorization)
    try:
        rtype = ResourceType(resource_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resource type")

    session = service.get_live_session(rtype, resource_id)
    return {
        "status": "OK",
        "state": {
            "cursors": session.get_cursors(),
            "selections": session.get_selections(),
            "participants": session.get_participants(),
        },
    }
