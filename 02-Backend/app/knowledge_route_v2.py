"""Knowledge System API routes (v2)."""

from fastapi import APIRouter, Header

from .knowledge_system import knowledge_system
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/index")
async def index_document(request: dict, authorization: str = Header(None)):
    """Index a document in the knowledge system."""
    get_user_id_from_token(authorization)
    result = knowledge_system.index_document(
        request.get("doc_id", ""),
        request.get("content", ""),
        request.get("metadata"),
        workspace_id=request.get("workspace_id", "default"),
    )
    return {"status": "OK", **result}


@router.post("/index/batch")
async def batch_index(request: dict, authorization: str = Header(None)):
    """Batch index multiple documents."""
    get_user_id_from_token(authorization)
    documents = request.get("documents", [])
    workspace_id = request.get("workspace_id", "default")
    job = knowledge_system.indexer.index_batch(documents, workspace_id=workspace_id)
    return {
        "status": "OK",
        "job_id": job.id,
        "indexed": job.indexed,
        "failed": job.failed,
        "errors": job.errors,
        "completed_at": job.completed_at,
    }


@router.get("/index/jobs/{job_id}")
async def get_index_job(job_id: str, authorization: str = Header(None)):
    """Get status of an indexing job."""
    get_user_id_from_token(authorization)
    job = knowledge_system.indexer.get_job_status(job_id)
    if not job:
        return {"status": "ERROR", "message": "job_not_found"}
    return {
        "status": "OK",
        "job_id": job.id,
        "state": job.status,
        "indexed": job.indexed,
        "failed": job.failed,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


@router.post("/index/optimize")
async def optimize_index(authorization: str = Header(None)):
    """Optimize the index by removing orphan nodes."""
    get_user_id_from_token(authorization)
    return {"status": "OK", **knowledge_system.indexer.optimize_index()}


@router.post("/entities/extract")
async def extract_entities(request: dict, authorization: str = Header(None)):
    """Extract entities from text."""
    get_user_id_from_token(authorization)
    text = request.get("text", "")
    doc_id = request.get("doc_id", "")
    workspace_id = request.get("workspace_id", "default")
    entities = knowledge_system.extractor.extract_with_metadata(
        text, doc_id=doc_id, workspace_id=workspace_id,
    )
    return {"status": "OK", "count": len(entities), "entities": entities}


@router.post("/entities/deduplicate")
async def deduplicate_entities(request: dict, authorization: str = Header(None)):
    """Deduplicate a list of entity dicts."""
    get_user_id_from_token(authorization)
    entities = request.get("entities", [])
    deduped = knowledge_system.extractor.deduplicate(entities)
    return {"status": "OK", "count": len(deduped), "entities": deduped}


@router.get("/search")
async def search_knowledge(q: str, limit: int = 10,
                            workspace_id: str = "default",
                            authorization: str = Header(None)):
    """Search the knowledge base."""
    get_user_id_from_token(authorization)
    results = knowledge_system.search_knowledge(q, limit, workspace_id=workspace_id)
    return {"status": "OK", "results": results}


@router.post("/search/context")
async def context_aware_search(request: dict, authorization: str = Header(None)):
    """Context-aware search with personalization signals."""
    get_user_id_from_token(authorization)
    query = request.get("query", "")
    context = request.get("context", {})
    limit = request.get("limit", 10)
    results = knowledge_system.context_aware_search(query, context, limit)
    return {"status": "OK", "results": results}


@router.get("/graph/{node_id}/related")
async def get_related(node_id: str, max_depth: int = 2,
                       authorization: str = Header(None)):
    """Get related nodes up to a depth."""
    get_user_id_from_token(authorization)
    related = knowledge_system.graph.get_related(node_id, max_depth=max_depth)
    return {
        "status": "OK",
        "related": [
            {"name": r["node"].name, "type": r["node"].node_type,
             "depth": r["depth"], "relationship": r["relationship"]}
            for r in related
        ],
    }


@router.get("/graph/{node_id}/path/{target_id}")
async def find_graph_path(node_id: str, target_id: str,
                           authorization: str = Header(None)):
    """Find path between two nodes."""
    get_user_id_from_token(authorization)
    path = knowledge_system.graph.find_path(node_id, target_id)
    return {"status": "OK", "path": path}


@router.post("/graph/infer")
async def infer_relationships(authorization: str = Header(None)):
    """Infer document-to-document relationships."""
    get_user_id_from_token(authorization)
    new_links = knowledge_system.infer_document_relationships()
    return {
        "status": "OK",
        "count": len(new_links),
        "relationships": [
            {
                "id": l.id, "doc_id_1": l.doc_id_1, "doc_id_2": l.doc_id_2,
                "strength": l.strength, "shared_entities": l.shared_entities,
            }
            for l in new_links
        ],
    }


@router.get("/graph/visualize")
async def visualize_graph(center_id: str = "", radius: int = 1,
                           format: str = "json",
                           authorization: str = Header(None)):
    """Get graph data prepared for visualization."""
    get_user_id_from_token(authorization)
    data = knowledge_system.visualize_graph(
        center_id=center_id or None, radius=radius, format=format,
    )
    return {"status": "OK", **data}


@router.get("/graph/clusters")
async def detect_clusters(authorization: str = Header(None)):
    """Detect clusters in the knowledge graph."""
    get_user_id_from_token(authorization)
    return {"status": "OK", "clusters": knowledge_system.graph.detect_clusters()}


@router.get("/graph/statistics")
async def graph_statistics(authorization: str = Header(None)):
    """Get graph statistics: density, degree, type distribution."""
    get_user_id_from_token(authorization)
    return {"status": "OK", **knowledge_system.graph.get_statistics()}


@router.post("/versions/{item_id}")
async def create_version(item_id: str, request: dict,
                          authorization: str = Header(None)):
    """Create a new version for an item."""
    user_id = get_user_id_from_token(authorization)
    version = knowledge_system.versioning.create_version(
        item_id=item_id,
        content=request.get("content", ""),
        change_description=request.get("change_description", ""),
        author=request.get("author") or user_id,
    )
    return {
        "status": "OK",
        "version_id": version.id,
        "version": version.version,
        "diff": version.diff,
    }


@router.get("/versions/{item_id}")
async def get_version_history(item_id: str,
                               authorization: str = Header(None)):
    """Get full version history of an item."""
    get_user_id_from_token(authorization)
    versions = knowledge_system.versioning.get_version_history(item_id)
    return {
        "status": "OK",
        "item_id": item_id,
        "count": len(versions),
        "versions": [
            {
                "id": v.id, "version": v.version,
                "created_at": v.created_at, "change_description": v.change_description,
                "author": v.author, "diff": v.diff,
            }
            for v in versions
        ],
    }


@router.get("/versions/{item_id}/compare")
async def compare_versions(item_id: str, v1: int, v2: int,
                            authorization: str = Header(None)):
    """Compare two versions of an item."""
    get_user_id_from_token(authorization)
    return {"status": "OK", **knowledge_system.versioning.compare(item_id, v1, v2)}


@router.post("/versions/{item_id}/rollback")
async def rollback_version(item_id: str, request: dict,
                            authorization: str = Header(None)):
    """Rollback to a specific version, creating a new version with old content."""
    user_id = get_user_id_from_token(authorization)
    version = request.get("version", 0)
    new_version = knowledge_system.versioning.rollback(
        item_id, version, author=request.get("author") or user_id,
    )
    if not new_version:
        return {"status": "ERROR", "message": "version_not_found"}
    return {
        "status": "OK",
        "rolled_back_to": version,
        "new_version": new_version.version,
        "version_id": new_version.id,
    }


@router.get("/versions/{item_id}/audit")
async def get_audit_trail(item_id: str, authorization: str = Header(None)):
    """Get audit trail for an item."""
    get_user_id_from_token(authorization)
    return {"status": "OK", "audit": knowledge_system.versioning.get_audit_trail(item_id)}


@router.get("/citations/{doc_id}")
async def get_doc_citations(doc_id: str, authorization: str = Header(None)):
    """Get citations from a document and references to it, with citation graph."""
    get_user_id_from_token(authorization)
    citations = knowledge_system.citations.get_citations(doc_id)
    references = knowledge_system.citations.get_references(doc_id)
    return {
        "status": "OK",
        "citations": [
            {"id": c.id, "target_doc_id": c.target_doc_id,
             "context": c.context, "locator": c.locator}
            for c in citations
        ],
        "references": [
            {"id": c.id, "source_doc_id": c.source_doc_id,
             "context": c.context, "locator": c.locator}
            for c in references
        ],
        "citation_graph": knowledge_system.citations.build_citation_graph(),
    }


@router.post("/citations")
async def add_citation(request: dict, authorization: str = Header(None)):
    """Add a citation between documents."""
    get_user_id_from_token(authorization)
    citation = knowledge_system.citations.add_citation(
        source_doc_id=request.get("source_doc_id", ""),
        target_doc_id=request.get("target_doc_id", ""),
        context=request.get("context", ""),
        locator=request.get("locator", ""),
        workspace_id=request.get("workspace_id", "default"),
    )
    return {
        "status": "OK",
        "id": citation.id,
        "formatted_apa": knowledge_system.citations.format_citation(citation, "APA"),
        "formatted_mla": knowledge_system.citations.format_citation(citation, "MLA"),
    }


@router.get("/analytics")
async def get_analytics(authorization: str = Header(None)):
    """Knowledge analytics dashboard."""
    get_user_id_from_token(authorization)
    return {"status": "OK", **knowledge_system.get_analytics()}


@router.get("/stats")
async def knowledge_stats(authorization: str = Header(None)):
    """Get basic knowledge system statistics."""
    get_user_id_from_token(authorization)
    return {"status": "OK", **knowledge_system.get_stats()}


@router.get("/workspaces/{workspace_id}")
async def get_workspace_knowledge(workspace_id: str,
                                    authorization: str = Header(None)):
    """Get knowledge scoped to a workspace."""
    get_user_id_from_token(authorization)
    return {"status": "OK", **knowledge_system.get_workspace_knowledge(workspace_id)}


@router.post("/nodes/{node_id}/share")
async def share_node(node_id: str, authorization: str = Header(None)):
    """Mark a knowledge node as shared/public across workspaces."""
    get_user_id_from_token(authorization)
    ok = knowledge_system.make_public(node_id)
    return {"status": "OK" if ok else "ERROR", "node_id": node_id, "is_public": ok}