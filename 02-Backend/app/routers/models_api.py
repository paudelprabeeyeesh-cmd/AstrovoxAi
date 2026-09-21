import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email, require_admin
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["models"])


@router.post("/models/register")
async def register_model(req: dict, user_id: str = Depends(require_admin)):
    model_id = str(uuid.uuid4())
    name = req.get("name", "unnamed")
    version = req.get("version", "1.0.0")
    provider = req.get("provider", "local")
    architecture = req.get("architecture", "transformer")
    parameters = req.get("parameters", "7B")
    snapshot_id = req.get("snapshot_id", f"{name}-{version}-{datetime.now().strftime('%Y%m%d')}")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO model_versions (id, name, version, provider, architecture, parameters, snapshot_id, enabled, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (model_id, name, version, provider, architecture, parameters, snapshot_id, 1, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": model_id, "name": name, "version": version, "snapshot_id": snapshot_id}


@router.get("/models")
async def list_models(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, version, provider, architecture, parameters, snapshot_id, enabled, created_at FROM model_versions WHERE enabled = 1 ORDER BY created_at DESC",
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/models/{model_id}")
async def get_model(model_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, version, provider, architecture, parameters, snapshot_id, enabled, created_at FROM model_versions WHERE id = ?",
            (model_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        return dict(row)


@router.post("/models/{model_id}/deploy")
async def deploy_model(model_id: str, user_id: str = Depends(require_admin)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, snapshot_id FROM model_versions WHERE id = ?",
            (model_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        conn.execute(
            "INSERT INTO model_deployments (id, model_id, status, deployed_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), model_id, "deployed", datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"model_id": model_id, "name": row["name"], "snapshot_id": row["snapshot_id"], "status": "deployed"}


@router.post("/models/{model_id}/deprecate")
async def deprecate_model(model_id: str, user_id: str = Depends(require_admin)):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM model_versions WHERE id = ?", (model_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        conn.execute("UPDATE model_versions SET enabled = 0 WHERE id = ?", (model_id,))
        conn.execute(
            "INSERT INTO model_deployments (id, model_id, status, deployed_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), model_id, "deprecated", datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"model_id": model_id, "deprecated": True}
