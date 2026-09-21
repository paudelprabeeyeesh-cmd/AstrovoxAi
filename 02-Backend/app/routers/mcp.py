import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mcp"])


@router.get("/mcp/tools")
async def list_mcp_tools(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, description, config, created_at FROM tools WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/mcp/tools")
async def register_mcp_tool(tool: dict, user_id: str = Depends(require_verified_email)):
    tool_id = str(uuid.uuid4())
    name = tool.get("name", "unnamed")
    description = tool.get("description", "")
    config = json.dumps(tool.get("config", {}))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tools (id, user_id, name, description, config, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (tool_id, user_id, name, description, config, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": tool_id, "name": name}


@router.post("/mcp/tools/{tool_id}/call")
async def call_mcp_tool(tool_id: str, args: dict, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, config FROM tools WHERE id = ? AND user_id = ?",
            (tool_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tool not found")
        config = json.loads(row["config"] or "{}")
        result = {
            "tool": row["name"],
            "args": args,
            "result": f"MCP tool {row['name']} executed with args {json.dumps(args)[:200]}",
            "config_used": list(config.keys()),
        }
    return result


@router.get("/mcp/servers")
async def list_mcp_servers(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, endpoint, enabled, created_at FROM mcp_servers WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/mcp/servers")
async def register_mcp_server(server: dict, user_id: str = Depends(require_verified_email)):
    server_id = str(uuid.uuid4())
    name = server.get("name", "unnamed")
    endpoint = server.get("endpoint", "")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO mcp_servers (id, user_id, name, endpoint, enabled, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (server_id, user_id, name, endpoint, 1, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": server_id, "name": name, "endpoint": endpoint}
