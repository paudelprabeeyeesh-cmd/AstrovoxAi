"""WebSocket endpoint — real-time communication."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from .websocket import ws_manager
from .notifications import notification_service

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    organization_id: str = Query(""),
    workspace_id: str = Query(""),
):
    """WebSocket connection for real-time updates."""
    conn_id = await ws_manager.connect(websocket, user_id, organization_id, workspace_id)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "workspace_id": workspace_id,
        })

        # Broadcast presence
        if workspace_id:
            await ws_manager.broadcast_to_workspace(
                workspace_id,
                {
                    "type": "presence",
                    "user_id": user_id,
                    "status": "online",
                },
                exclude_user=user_id,
            )

        # Message loop
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "typing":
                await ws_manager.broadcast_to_workspace(
                    workspace_id,
                    {
                        "type": "typing",
                        "user_id": user_id,
                        "is_typing": data.get("is_typing", True),
                    },
                    exclude_user=user_id,
                )

            elif msg_type == "message":
                await ws_manager.broadcast_to_workspace(
                    workspace_id,
                    {
                        "type": "message",
                        "user_id": user_id,
                        "content": data.get("content", ""),
                        "timestamp": data.get("timestamp", 0),
                    },
                )

            elif msg_type == "presence_request":
                presence = ws_manager.get_workspace_presence(workspace_id)
                await websocket.send_json({
                    "type": "presence_update",
                    "users": presence,
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(conn_id)
        if workspace_id:
            await ws_manager.broadcast_to_workspace(
                workspace_id,
                {
                    "type": "presence",
                    "user_id": user_id,
                    "status": "offline",
                },
            )
