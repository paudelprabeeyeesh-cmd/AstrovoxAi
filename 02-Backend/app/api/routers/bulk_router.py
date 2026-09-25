"""Bulk create/update/delete endpoints with transaction semantics."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.database_helpers.batch import BatchUpsert
from app.database_helpers.retry import TransactionRetry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bulk", tags=["bulk"])


class BulkItemCreate(BaseModel):
    data: Dict[str, Any] = Field(..., description="Item payload")


class BulkItemUpdate(BaseModel):
    id: str = Field(..., description="Item identifier")
    data: Dict[str, Any] = Field(..., description="Fields to update")


class BulkItemDelete(BaseModel):
    id: str = Field(..., description="Item identifier")


class BulkCreateRequest(BaseModel):
    items: List[BulkItemCreate] = Field(..., min_length=1, max_length=1000)
    table: str = Field(..., description="Target table name")
    conflict_columns: List[str] = Field(default_factory=list, description="Columns for conflict resolution")
    returning: bool = Field(default=False, description="Return created rows")


class BulkUpdateRequest(BaseModel):
    items: List[BulkItemUpdate] = Field(..., min_length=1, max_length=1000)
    table: str = Field(..., description="Target table name")
    conflict_columns: List[str] = Field(default_factory=list, description="Columns for conflict resolution")


class BulkDeleteRequest(BaseModel):
    ids: List[str] = Field(..., min_length=1, max_length=1000)
    table: str = Field(..., description="Target table name")


class BulkResultItem(BaseModel):
    index: int
    id: Optional[str] = None
    success: bool
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class BulkResponse(BaseModel):
    success: bool
    created: int = 0
    updated: int = 0
    deleted: int = 0
    failed: int = 0
    results: List[BulkResultItem] = Field(default_factory=list)


def _get_engine() -> Any:
    try:
        from app.database_engine import connection_pool
        return connection_pool
    except Exception:
        pass
    try:
        from app.database import get_db
        return get_db()
    except Exception:
        return None


@router.post("/create", response_model=BulkResponse)
async def bulk_create(request: BulkCreateRequest):
    results: List[BulkResultItem] = []
    created = 0
    failed = 0

    if not request.items:
        return BulkResponse(success=True, created=0, failed=0, results=results)

    rows = [item.data for item in request.items]
    conflict_columns = request.conflict_columns or list(rows[0].keys())[:1] if rows else []

    try:
        engine = _get_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="Database engine not available")

        retry = TransactionRetry(max_retries=3, base_delay=0.1)

        def _upsert() -> int:
            batch = BatchUpsert(engine)
            return batch.upsert(
                request.table,
                rows,
                conflict_columns=conflict_columns,
                update_columns=None,
                return_defaults=request.returning,
            )

        count = retry.run(_upsert)
        created = count
        for idx, item in enumerate(request.items):
            results.append(BulkResultItem(index=idx, success=True, data=item.data))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Bulk create failed: %s", exc)
        for idx, item in enumerate(request.items):
            results.append(BulkResultItem(index=idx, success=False, error=str(exc)))
            failed += 1

    return BulkResponse(success=failed == 0, created=created, failed=failed, results=results)


@router.post("/update", response_model=BulkResponse)
async def bulk_update(request: BulkUpdateRequest):
    results: List[BulkResultItem] = []
    updated = 0
    failed = 0

    if not request.items:
        return BulkResponse(success=True, updated=0, failed=0, results=results)

    rows = [{"id": item.id, **item.data} for item in request.items]
    conflict_columns = request.conflict_columns or ["id"]

    try:
        engine = _get_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="Database engine not available")

        retry = TransactionRetry(max_retries=3, base_delay=0.1)

        def _upsert() -> int:
            batch = BatchUpsert(engine)
            return batch.upsert(
                request.table,
                rows,
                conflict_columns=conflict_columns,
                update_columns=None,
            )

        count = retry.run(_upsert)
        updated = count
        for idx, item in enumerate(request.items):
            results.append(BulkResultItem(index=idx, id=item.id, success=True, data=item.data))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Bulk update failed: %s", exc)
        for idx, item in enumerate(request.items):
            results.append(BulkResultItem(index=idx, id=item.id, success=False, error=str(exc)))
            failed += 1

    return BulkResponse(success=failed == 0, updated=updated, failed=failed, results=results)


@router.post("/delete", response_model=BulkResponse)
async def bulk_delete(request: BulkDeleteRequest):
    results: List[BulkResultItem] = []
    deleted = 0
    failed = 0

    if not request.ids:
        return BulkResponse(success=True, deleted=0, failed=0, results=results)

    try:
        engine = _get_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="Database engine not available")

        retry = TransactionRetry(max_retries=3, base_delay=0.1)

        def _delete() -> int:
            conn = engine.get_session() if hasattr(engine, "get_session") else engine
            try:
                from sqlalchemy import text
                count = 0
                for item_id in request.ids:
                    result = conn.execute(text(f"DELETE FROM {request.table} WHERE id = :id"), {"id": item_id})
                    count += result.rowcount or 0
                if hasattr(conn, "commit"):
                    conn.commit()
                return count
            finally:
                if hasattr(conn, "close"):
                    conn.close()

        count = retry.run(_delete)
        deleted = count
        for idx, item_id in enumerate(request.ids):
            results.append(BulkResultItem(index=idx, id=item_id, success=True))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Bulk delete failed: %s", exc)
        for idx, item_id in enumerate(request.ids):
            results.append(BulkResultItem(index=idx, id=item_id, success=False, error=str(exc)))
            failed += 1

    return BulkResponse(success=failed == 0, deleted=deleted, failed=failed, results=results)
