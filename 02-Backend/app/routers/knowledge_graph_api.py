import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge-graph"])


@router.post("/knowledge-graph/entities")
async def create_entity(entity: dict, user_id: str = Depends(require_verified_email)):
    entity_id = str(uuid.uuid4())
    entity_type = entity.get("entity_type", "concept")
    name = entity.get("name", "")
    properties = json.dumps(entity.get("properties", {}))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO knowledge_entities (id, user_id, entity_type, name, properties, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (entity_id, user_id, entity_type, name, properties, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": entity_id, "name": name, "entity_type": entity_type}


@router.get("/knowledge-graph/entities")
async def list_entities(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, entity_type, name, properties, created_at FROM knowledge_entities WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
            (user_id,),
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["properties"] = json.loads(item.get("properties", "{}"))
            result.append(item)
        return result


@router.post("/knowledge-graph/relationships")
async def create_relationship(rel: dict, user_id: str = Depends(require_verified_email)):
    rel_id = str(uuid.uuid4())
    source_name = rel.get("source_name", "")
    target_name = rel.get("target_name", "")
    rel_type = rel.get("relationship_type", "related_to")
    properties = json.dumps(rel.get("properties", {}))
    with get_db() as conn:
        source = conn.execute(
            "SELECT id FROM knowledge_entities WHERE user_id = ? AND name = ?",
            (user_id, source_name),
        ).fetchone()
        target = conn.execute(
            "SELECT id FROM knowledge_entities WHERE user_id = ? AND name = ?",
            (user_id, target_name),
        ).fetchone()
        if not source or not target:
            raise HTTPException(status_code=404, detail="Source or target entity not found")
        conn.execute(
            "INSERT INTO knowledge_relationships (id, user_id, source_id, target_id, relationship_type, properties, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rel_id, user_id, source["id"], target["id"], rel_type, properties, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": rel_id, "source": source_name, "target": target_name, "type": rel_type}


@router.get("/knowledge-graph/traverse")
async def traverse_graph(start_entity: str, max_depth: int = 2, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        start = conn.execute(
            "SELECT id, name FROM knowledge_entities WHERE user_id = ? AND name = ?",
            (user_id, start_entity),
        ).fetchone()
        if not start:
            raise HTTPException(status_code=404, detail="Entity not found")
        rows = conn.execute(
            "SELECT r.relationship_type, e.name, e.entity_type FROM knowledge_relationships r JOIN knowledge_entities e ON e.id = r.target_id WHERE r.source_id = ? AND r.user_id = ? LIMIT 50",
            (start["id"], user_id),
        ).fetchall()
        connections = [{"entity": r["name"], "type": r["entity_type"], "relationship": r["relationship_type"]} for r in rows]
    return {"start": start_entity, "connections": connections}
