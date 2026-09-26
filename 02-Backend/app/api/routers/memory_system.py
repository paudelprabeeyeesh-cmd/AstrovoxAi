"""Unified memory system API endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.services.memory_system import (
    MemoryCategory,
    MemoryTier,
    ConflictStrategy,
    KnowledgeNode,
    KnowledgeEdge,
    get_memory_system,
)
from app.utils.auth.auth_utils import get_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory-system", tags=["memory-system"])

memory_system = get_memory_system()


class RememberRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    category: str = Field("fact", max_length=50)
    tier: str = Field("medium", max_length=20)
    importance: float = Field(1.0, ge=0.0, le=1.0)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_explicit: bool = False


class EditMemoryRequest(BaseModel):
    memory_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1, max_length=10000)
    metadata: Optional[Dict[str, Any]] = None


class RecallRequest(BaseModel):
    query: str = Field("", max_length=1000)
    category: Optional[str] = None
    tier: Optional[str] = None
    limit: int = Field(10, ge=1, le=100)


class UserPreferenceRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=200)
    value: Any = Field(...)


class KnowledgeNodeRequest(BaseModel):
    node_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=500)
    node_type: str = Field(..., min_length=1, max_length=100)
    properties: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdgeRequest(BaseModel):
    edge_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)
    relation: str = Field(..., min_length=1, max_length=200)
    properties: Dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(1.0, ge=0.0)


class ConflictResolveRequest(BaseModel):
    strategy: str = Field("newest", max_length=20)


def _user_id(authorization: str = Header(None)) -> str:
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return str(user_id)


def _category(category: Optional[str]) -> Optional[MemoryCategory]:
    if not category:
        return None
    try:
        return MemoryCategory(category)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid category: {category}")


def _tier(tier: Optional[str]) -> Optional[MemoryTier]:
    if not tier:
        return None
    try:
        return MemoryTier(tier)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid tier: {tier}")


@router.post("/remember")
async def remember(request: RememberRequest, authorization: str = Header(None)):
    user_id = _user_id(authorization)
    fragment = memory_system.remember(
        user_id=user_id,
        content=request.content,
        category=_category(request.category) or MemoryCategory.FACT,
        tier=_tier(request.tier) or MemoryTier.MEDIUM,
        importance=request.importance,
        confidence=request.confidence,
        tags=request.tags,
        metadata=request.metadata,
        user_explicit=request.user_explicit,
    )
    return {"status": "OK", "memory": fragment.to_dict()}


@router.post("/recall")
async def recall(request: RecallRequest, authorization: str = Header(None)):
    user_id = _user_id(authorization)
    fragments = memory_system.recall(
        user_id=user_id,
        query=request.query,
        category=_category(request.category),
        tier=_tier(request.tier),
        limit=request.limit,
    )
    return {"status": "OK", "memories": [f.to_dict() for f in fragments]}


@router.get("/memory/{memory_id}")
async def get_memory(memory_id: str, authorization: str = Header(None)):
    _user_id(authorization)
    fragment = memory_system.get_memory(memory_id)
    if not fragment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return {"status": "OK", "memory": fragment.to_dict()}


@router.put("/memory/{memory_id}")
async def edit_memory(memory_id: str, request: EditMemoryRequest, authorization: str = Header(None)):
    _user_id(authorization)
    if memory_id != request.memory_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Memory ID mismatch")
    fragment = memory_system.edit_memory(memory_id, request.content, request.metadata)
    if not fragment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return {"status": "OK", "memory": fragment.to_dict()}


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: str, authorization: str = Header(None)):
    _user_id(authorization)
    ok = memory_system.delete_memory(memory_id, soft=True)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return {"status": "OK", "deleted": True, "memory_id": memory_id}


@router.post("/preferences")
async def set_user_preference(request: UserPreferenceRequest, authorization: str = Header(None)):
    user_id = _user_id(authorization)
    fragment = memory_system.add_user_preference(user_id, request.key, request.value)
    return {"status": "OK", "preference": fragment.to_dict()}


@router.get("/preferences")
async def get_user_preferences(authorization: str = Header(None)):
    user_id = _user_id(authorization)
    preferences = memory_system.get_user_preferences(user_id)
    return {"status": "OK", "preferences": [p.to_dict() for p in preferences]}


@router.post("/knowledge/nodes")
async def add_knowledge_node(request: KnowledgeNodeRequest, authorization: str = Header(None)):
    _user_id(authorization)
    node = KnowledgeNode(
        node_id=request.node_id,
        name=request.name,
        node_type=request.node_type,
        properties=request.properties,
    )
    memory_system.add_knowledge_node(node)
    return {"status": "OK", "node": {"node_id": node.node_id, "name": node.name, "node_type": node.node_type}}


@router.post("/knowledge/edges")
async def add_knowledge_edge(request: KnowledgeEdgeRequest, authorization: str = Header(None)):
    _user_id(authorization)
    edge = KnowledgeEdge(
        edge_id=request.edge_id,
        source_id=request.source_id,
        target_id=request.target_id,
        relation=request.relation,
        properties=request.properties,
        weight=request.weight,
    )
    memory_system.add_knowledge_edge(edge)
    return {"status": "OK", "edge": {"edge_id": edge.edge_id, "relation": edge.relation}}


@router.get("/knowledge/related/{node_id}")
async def get_related_knowledge(node_id: str, authorization: str = Header(None)):
    _user_id(authorization)
    nodes = memory_system.get_related_knowledge(node_id, depth=2)
    return {"status": "OK", "nodes": [{"node_id": n.node_id, "name": n.name, "node_type": n.node_type} for n in nodes]}


@router.get("/conflicts")
async def get_conflicts(authorization: str = Header(None)):
    user_id = _user_id(authorization)
    conflicts = memory_system.detect_conflicts(user_id)
    return {
        "status": "OK",
        "conflicts": [
            {
                "memory_a": a.to_dict(),
                "memory_b": b.to_dict(),
                "conflict_type": ctype,
            }
            for a, b, ctype in conflicts
        ],
    }


@router.post("/conflicts/resolve")
async def resolve_conflicts(request: ConflictResolveRequest, authorization: str = Header(None)):
    user_id = _user_id(authorization)
    try:
        strategy = ConflictStrategy(request.strategy)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid strategy: {request.strategy}")
    resolved = memory_system.resolve_conflicts(user_id, strategy)
    return {"status": "OK", "resolved": [r.to_dict() for r in resolved]}


@router.post("/prioritize")
async def prioritize_context(request: RecallRequest, authorization: str = Header(None)):
    user_id = _user_id(authorization)
    memories = memory_system.prioritize_context(user_id, request.query, limit=request.limit)
    return {"status": "OK", "memories": [m.to_dict() for m in memories]}


@router.post("/compress")
async def compress_memories(authorization: str = Header(None)):
    user_id = _user_id(authorization)
    compressed = memory_system.auto_compress(user_id)
    return {"status": "OK", "compressed": compressed}


@router.post("/decay")
async def decay_memories(authorization: str = Header(None)):
    user_id = _user_id(authorization)
    count = memory_system.decay_all(user_id)
    return {"status": "OK", "decayed": count}


@router.post("/prune")
async def prune_memories(authorization: str = Header(None), threshold: float = 0.05):
    user_id = _user_id(authorization)
    removed = memory_system.prune(user_id, threshold=threshold)
    return {"status": "OK", "removed": len(removed), "memory_ids": removed}


@router.get("/stats")
async def get_stats(authorization: str = Header(None)):
    user_id = _user_id(authorization)
    return {"status": "OK", "stats": memory_system.get_stats(user_id)}


@router.get("/summarize/{memory_id}")
async def summarize_memory(memory_id: str, authorization: str = Header(None)):
    _user_id(authorization)
    fragment = memory_system.get_memory(memory_id)
    if not fragment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    from app.services.memory_system import MemoryCompressor
    summary = MemoryCompressor.summarize_for_context(fragment.content)
    return {"status": "OK", "summary": summary, "memory_id": memory_id}
