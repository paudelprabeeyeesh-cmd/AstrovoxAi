"""WebSocket and Tools API routes."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional

from .realtime import connection_manager, background_worker
from .tools import tool_registry
from .ai_security_enhanced import pii_detector, secret_detector, conversation_limiter
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/realtime", tags=["realtime"])


@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str = "",
):
    """WebSocket endpoint for real-time chat."""
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    try:
        from .auth_utils import get_user_id_from_token
        user_id = get_user_id_from_token(f"Bearer {token}")
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    conn_id = await connection_manager.connect(websocket, user_id, conversation_id)

    try:
        await connection_manager.send_message(conn_id, {
            "type": "connected",
            "conversation_id": conversation_id,
            "user_id": user_id,
        })

        while True:
            data = await websocket.receive_text()
            message = {"type": "ack", "received": data}

            if data.startswith("typing:"):
                is_typing = data.replace("typing:", "") == "true"
                await connection_manager.broadcast_typing(user_id, conversation_id, is_typing)
            elif data.startswith("message:"):
                content = data.replace("message:", "")
                await connection_manager.broadcast_to_conversation(
                    conversation_id,
                    {"type": "message", "user_id": user_id, "content": content},
                    exclude=conn_id,
                )

            await connection_manager.send_message(conn_id, message)

    except WebSocketDisconnect:
        connection_manager.disconnect(conn_id)
    except Exception as e:
        connection_manager.disconnect(conn_id)


@router.get("/connections")
async def get_connections(authorization: str = Header(None)):
    """Get active connection count."""
    user_id = get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "total_connections": connection_manager.get_connection_count(),
    }


@router.get("/workers")
async def get_worker_stats(authorization: str = Header(None)):
    """Get background worker stats."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", **background_worker.get_stats()}


# Tools API

tools_router = APIRouter(prefix="/tools", tags=["tools"])


@tools_router.get("/")
async def list_tools(authorization: str = Header(None)):
    """List available tools."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "tools": tool_registry.get_tools()}


class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: dict = {}


@tools_router.post("/execute")
async def execute_tool(request: ToolExecuteRequest, authorization: str = Header(None)):
    """Execute a tool."""
    user_id = get_user_id_from_token(authorization)

    result = await tool_registry.execute(request.tool_name, **request.parameters)

    return {
        "status": "OK" if result.success else "ERROR",
        "result": result.result,
        "tool": result.tool_name,
        "metadata": result.metadata,
    }


# Security scanning API

security_router = APIRouter(prefix="/security-scan", tags=["security"])


class ScanRequest(BaseModel):
    text: str


@security_router.post("/pii")
async def scan_pii(request: ScanRequest, authorization: str = Header(None)):
    """Scan text for PII."""
    user_id = get_user_id_from_token(authorization)
    result = pii_detector.scan(request.text)
    return {
        "status": "OK",
        "safe": result.safe,
        "issues": result.issues,
        "sanitized": result.sanitized,
        "risk_score": result.risk_score,
    }


@security_router.post("/secrets")
async def scan_secrets(request: ScanRequest, authorization: str = Header(None)):
    """Scan text for secrets."""
    user_id = get_user_id_from_token(authorization)
    result = secret_detector.scan(request.text)
    return {
        "status": "OK",
        "safe": result.safe,
        "issues": result.issues,
        "sanitized": result.sanitized,
        "risk_score": result.risk_score,
    }
