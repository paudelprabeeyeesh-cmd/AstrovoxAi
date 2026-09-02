"""Knowledge System API routes."""

from fastapi import APIRouter, Header

from .knowledge_system import knowledge_system
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/index")
async def index_document(request: dict, authorization: str = Header(None)):
    """Index a document in the knowledge system."""
    user_id = get_user_id_from_token(authorization)
    result = knowledge_system.index_document(
        request.get("doc_id", ""),
        request.get("content", ""),
        request.get("metadata"),
    )
    return {"status": "OK", **result}


@router.get("/search")
async def search_knowledge(q: str, limit: int = 10, authorization: str = Header(None)):
    """Search the knowledge base."""
    user_id = get_user_id_from_token(authorization)
    results = knowledge_system.search_knowledge(q, limit)
    return {"status": "OK", "results": results}


@router.get("/graph/{node_id}/related")
async def get_related(node_id: str, authorization: str = Header(None)):
    """Get related nodes."""
    user_id = get_user_id_from_token(authorization)
    related = knowledge_system.graph.get_related(node_id)
    return {
        "status": "OK",
        "related": [{"name": n.name, "type": n.node_type} for n in related],
    }


@router.get("/stats")
async def knowledge_stats(authorization: str = Header(None)):
    """Get knowledge system statistics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", **knowledge_system.get_stats()}
