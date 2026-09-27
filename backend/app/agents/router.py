"""Agents API router."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .tools import ToolRegistry

logger = logging.getLogger(__name__)
tool_registry = ToolRegistry()
router = APIRouter(prefix="/agents", tags=["agents"])


class ToolExecutionRequest(BaseModel):
    tool: str = Field(..., min_length=1)
    params: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    message: str


@router.get("/tools")
async def list_tools():
    return tool_registry.list_tools()


@router.post("/tools/execute")
async def execute_tool(body: ToolExecutionRequest):
    result = tool_registry.execute(body.tool, **body.params)
    return result
