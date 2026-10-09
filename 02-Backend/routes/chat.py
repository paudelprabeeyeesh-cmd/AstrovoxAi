from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()


class MessageRequest(BaseModel):
    conversation_id: str
    role: str = "user"
    content: str = ""


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str


conversations_store: dict[str, dict] = {}
messages_store: dict[str, list[dict]] = {}


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().timestamp()}"


@router.post("/conversations")
async def create_conversation(user_id: Optional[str] = None):
    conv_id = _generate_id("conv")
    conversations_store[conv_id] = {
        "id": conv_id,
        "user_id": user_id,
        "title": "New conversation",
        "created_at": datetime.now().isoformat(),
    }
    messages_store.setdefault(conv_id, [])
    return {"status": "OK", "conversation": conversations_store[conv_id]}


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    if conversation_id not in conversations_store:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "status": "OK",
        "messages": messages_store.get(conversation_id, []),
        "count": len(messages_store.get(conversation_id, [])),
    }


@router.post("/message", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    if request.conversation_id not in conversations_store:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msg_id = _generate_id("msg")
    msg = {
        "id": msg_id,
        "conversation_id": request.conversation_id,
        "role": request.role,
        "content": request.content,
        "created_at": datetime.now().isoformat(),
    }
    messages_store.setdefault(request.conversation_id, []).append(msg)
    return msg


@router.get("/models")
async def list_models():
    return {
        "status": "OK",
        "models": [
            {"id": "gpt-4", "provider": "openai", "display_name": "GPT-4"},
            {"id": "claude-3", "provider": "anthropic", "display_name": "Claude 3"},
        ],
    }
