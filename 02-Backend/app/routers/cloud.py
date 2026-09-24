"""Cloud infrastructure router for AstrovoxAI backend."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.cloud_storage import cloud_storage, StorageObject
from app.cdn import cdn_service
from app.load_balancer_config import load_balancer, BackendNode
from app.auto_scaling import auto_scaler
from app.multi_region import multi_region_manager, RegionConfig, RegionStrategy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cloud", tags=["cloud"])


class StorageUploadRequest(BaseModel):
    bucket: str = Field(..., min_length=1)
    key: str = Field(..., min_length=1)
    content: str
    content_type: str = "application/octet-stream"


class StorageUploadResponse(BaseModel):
    bucket: str
    key: str
    url: Optional[str] = None
    size: int


class PurgeRequest(BaseModel):
    urls: Optional[List[str]] = None
    prefix: Optional[str] = None


class NodeRegisterRequest(BaseModel):
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100


class RegionResponse(BaseModel):
    name: str
    code: str
    provider: str
    primary: bool


@router.get("/regions", response_model=List[RegionResponse])
async def list_regions() -> List[Dict[str, Any]]:
    regions = multi_region_manager.get_regions()
    return [
        {
            "name": r.name,
            "code": r.code,
            "provider": r.provider,
            "primary": r.primary,
        }
        for r in regions
    ]


@router.get("/regions/primary", response_model=RegionResponse)
async def get_primary_region() -> Dict[str, Any]:
    region = multi_region_manager.get_primary_region()
    if not region:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No primary region configured")
    return {
        "name": region.name,
        "code": region.code,
        "provider": region.provider,
        "primary": region.primary,
    }


@router.post("/regions/resolve")
async def resolve_region(country: str = "", latency_ms: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    region = multi_region_manager.resolve_region(user_country=country, latency_ms=latency_ms)
    return {
        "name": region.name,
        "code": region.code,
        "provider": region.provider,
    }


@router.post("/storage/upload", response_model=StorageUploadResponse)
async def upload_to_storage(request: StorageUploadRequest) -> Dict[str, Any]:
    try:
        obj = cloud_storage.upload(
            bucket=request.bucket,
            key=request.key,
            data=request.content,
            content_type=request.content_type,
        )
        url = cloud_storage.get_public_url(request.bucket, request.key)
        return {
            "bucket": obj.bucket,
            "key": obj.key,
            "url": url,
            "size": obj.size,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Storage upload failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete("/storage/{bucket}/{path:path}")
async def delete_from_storage(bucket: str, path: str) -> Dict[str, Any]:
    try:
        deleted = cloud_storage.delete(bucket, path)
        return {"deleted": deleted}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/storage/{bucket}/objects")
async def list_storage_objects(bucket: str, prefix: str = "") -> Dict[str, Any]:
    try:
        objects = cloud_storage.list_objects(bucket, prefix=prefix)
        return {
            "bucket": bucket,
            "objects": [
                {
                    "key": obj.key,
                    "size": obj.size,
                    "content_type": obj.content_type,
                    "last_modified": obj.last_modified,
                }
                for obj in objects
            ],
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/storage/{bucket}/{path:path}/url")
async def get_storage_url(bucket: str, path: str, expires_in: int = 3600) -> Dict[str, Any]:
    try:
        url = cloud_storage.get_presigned_url(bucket, path, expires_in=expires_in)
        return {"url": url}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/cdn/purge")
async def purge_cdn(request: PurgeRequest) -> Dict[str, Any]:
    try:
        if request.urls:
            purged = cdn_service.purge_urls(request.urls)
        elif request.prefix:
            purged = cdn_service.purge_prefix(request.prefix)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="urls or prefix required")
        return {"purged": purged}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/load-balancer/nodes")
async def register_backend_node(request: NodeRegisterRequest) -> Dict[str, Any]:
    node = BackendNode(host=request.host, port=request.port, weight=request.weight, max_connections=request.max_connections)
    load_balancer.register_node(node)
    return {"registered": node.address}


@router.delete("/load-balancer/nodes/{host}:{port}")
async def deregister_backend_node(host: str, port: int) -> Dict[str, Any]:
    load_balancer.deregister_node(f"{host}:{port}")
    return {"deregistered": f"{host}:{port}"}


@router.get("/load-balancer/stats")
async def get_load_balancer_stats() -> Dict[str, Any]:
    return load_balancer.get_stats()


@router.get("/auto-scaling/status")
async def get_auto_scaling_status() -> Dict[str, Any]:
    return {
        "current_instances": auto_scaler.current_instances,
        "min_instances": auto_scaler.policy.min_instances,
        "max_instances": auto_scaler.policy.max_instances,
    }
