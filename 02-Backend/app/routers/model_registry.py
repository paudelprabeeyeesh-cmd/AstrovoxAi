import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException

from ..auth import require_admin, require_verified_email
from ..database import get_db
from ..ml.model_registry import ModelRegistry
from ..model_catalog import model_router as catalog_router
from ..schemas import ModelDropdownItem, ModelRegistryEntryCreate, ModelRegistryEntryOut

logger = logging.getLogger(__name__)

router = APIRouter(tags=["model-registry"])

_registry = ModelRegistry()


@router.get("/models/dropdown", response_model=list[ModelDropdownItem])
async def list_models_for_dropdown(_: str = Depends(require_verified_email)):
    items: list[ModelDropdownItem] = []
    for m in catalog_router.list_models():
        items.append(ModelDropdownItem(
            id=m["model_id"],
            name=m["model_id"],
            provider=m["provider"],
            model_id=m["model_id"],
            stage="catalog",
            source="catalog",
        ))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, version, provider, model_id, stage FROM model_registry_entries ORDER BY created_at DESC"
        ).fetchall()
        for r in rows:
            items.append(ModelDropdownItem(
                id=r["id"],
                name=r["name"],
                provider=r["provider"],
                model_id=r["model_id"],
                stage=r["stage"],
                source="registry",
            ))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, model, status, fine_tuned_model FROM finetuning_jobs WHERE status = 'completed' ORDER BY completed_at DESC"
        ).fetchall()
        for r in rows:
            model_name = r.get("fine_tuned_model") or f"ft-job-{r['id'][:8]}"
            items.append(ModelDropdownItem(
                id=r["id"],
                name=model_name,
                provider="custom",
                model_id=model_name,
                stage="production",
                source="finetuned",
            ))
    return items


@router.get("/models/registry", response_model=list[ModelRegistryEntryOut])
async def list_registered_models(_: str = Depends(require_admin)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, version, provider, model_id, stage, metadata, created_at FROM model_registry_entries ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            result.append(ModelRegistryEntryOut(
                id=r["id"],
                name=r["name"],
                version=r["version"],
                provider=r["provider"],
                model_id=r["model_id"],
                stage=r["stage"],
                metadata=r.get("metadata"),
                created_at=datetime.fromisoformat(r["created_at"]) if r.get("created_at") else datetime.now(timezone.utc),
            ))
        return result


@router.post("/models/registry", response_model=ModelRegistryEntryOut)
async def register_model_entry(req: ModelRegistryEntryCreate, _: str = Depends(require_admin)):
    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO model_registry_entries (id, name, version, provider, model_id, stage, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (entry_id, req.name, req.version, req.provider, req.model_id, req.stage, str(req.metadata or {}), now),
        )
        conn.commit()
    _registry.register_model(req.name, req.version, req.model_id, req.metadata)
    return ModelRegistryEntryOut(
        id=entry_id,
        name=req.name,
        version=req.version,
        provider=req.provider,
        model_id=req.model_id,
        stage=req.stage,
        metadata=req.metadata,
        created_at=datetime.now(timezone.utc),
    )


@router.get("/models/registry/{entry_id}", response_model=ModelRegistryEntryOut)
async def get_registered_model(entry_id: str, _: str = Depends(require_admin)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, version, provider, model_id, stage, metadata, created_at FROM model_registry_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        return ModelRegistryEntryOut(
            id=row["id"],
            name=row["name"],
            version=row["version"],
            provider=row["provider"],
            model_id=row["model_id"],
            stage=row["stage"],
            metadata=row.get("metadata"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(timezone.utc),
        )


@router.post("/models/registry/{entry_id}/promote")
async def promote_model(entry_id: str, stage: str = Form(...), _: str = Depends(require_admin)):
    if stage not in {"development", "staging", "production"}:
        raise HTTPException(status_code=400, detail="Invalid stage")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM model_registry_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        conn.execute(
            "UPDATE model_registry_entries SET stage = ? WHERE id = ?",
            (stage, entry_id),
        )
        conn.commit()
    _registry.promote_model(entry_id, stage)
    return {"id": entry_id, "stage": stage}
