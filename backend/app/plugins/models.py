"""Pydantic models for plugin system."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class PluginStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class PluginManifest(BaseModel):
    id: str
    name: str
    version: str
    description: str
    author: str
    entrypoint: str
    permissions: list[str] = Field(default_factory=list)
    config_schema: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)


class PluginInfo(PluginManifest):
    status: PluginStatus
    installed_at: datetime
    last_used: Optional[datetime] = None
    error_message: Optional[str] = None


class PluginExecutionRequest(BaseModel):
    plugin_id: str
    method: str
    params: dict = Field(default_factory=dict)
    timeout: int = Field(default=30, ge=1, le=300)


class PluginExecutionResponse(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float
