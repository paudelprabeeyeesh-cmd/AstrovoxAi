"""Plugin API router."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import os

from .models import PluginInfo, PluginExecutionRequest, PluginExecutionResponse
from .loader import PluginLoader

logger = logging.getLogger(__name__)
plugin_loader = PluginLoader()
router = APIRouter(prefix="/plugins", tags=["plugins"])


class MessageResponse(BaseModel):
    message: str


class InstallPluginRequest(BaseModel):
    name: str
    source: str


@router.get("/", response_model=list[PluginInfo])
async def list_plugins():
    return plugin_loader._registry.list_plugins()


@router.post("/discover", response_model=list[str])
async def discover_plugins():
    return plugin_loader.discover()


@router.post("/load", response_model=list[Any])
async def load_plugins():
    return plugin_loader.load_all()


@router.post("/install", response_model=PluginInfo, status_code=status.HTTP_201_CREATED)
async def install_plugin(body: InstallPluginRequest):
    path = body.source
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin source not found")
    manifest = plugin_loader.load_plugin(path)
    return plugin_loader._registry.get_plugin(manifest.id)


@router.post("/execute", response_model=PluginExecutionResponse)
async def execute_plugin(body: PluginExecutionRequest):
    try:
        import time
        start = time.time()
        result = plugin_loader.execute(body.plugin_id, body.method, body.params)
        duration = (time.time() - start) * 1000
        return PluginExecutionResponse(success=True, result=result, duration_ms=duration)
    except Exception as exc:
        return PluginExecutionResponse(success=False, error=str(exc), duration_ms=0.0)


@router.delete("/{plugin_id}", response_model=MessageResponse)
async def uninstall_plugin(plugin_id: str):
    if not plugin_loader._registry.unregister(plugin_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")
    return MessageResponse(message="Plugin uninstalled successfully")
