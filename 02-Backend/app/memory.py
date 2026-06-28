from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from .auth_utils import get_user_id_from_token
from .database import (
    save_memory,
    get_user_memory,
    get_recent_messages,
)

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryEntry(BaseModel):
    content: str
    importance: Optional[int] = 1


class MemoryResponse(BaseModel):
    id: int
    user_id: str
    content: str
    importance: int
    created_at: str


@router.post("/save")
async def save_memory_entry(entry: MemoryEntry, authorization: str = Header(None)):
    """Save a memory entry"""
    user_id = get_user_id_from_token(authorization)

    try:
        memory = await save_memory(user_id, entry.content, entry.importance)
        return {"status": "OK", "memory": memory}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save memory: {str(e)}",
        )


@router.get("/")
async def get_memory(authorization: str = Header(None), limit: int = 50):
    """Get user's memory entries"""
    user_id = get_user_id_from_token(authorization)

    try:
        memory = await get_user_memory(user_id, limit)
        return {"status": "OK", "memory": memory, "count": len(memory)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch memory: {str(e)}",
        )


@router.post("/extract-from-conversation")
async def extract_memory_from_conversation(
    conversation_id: int, authorization: str = Header(None)
):
    """Extract important information from a conversation and save as memory"""
    user_id = get_user_id_from_token(authorization)

    try:
        # Get recent messages from conversation
        messages = await get_recent_messages(conversation_id, limit=20)

        if not messages:
            return {
                "status": "OK",
                "message": "No messages to extract from",
                "extracted": [],
            }

        # Extract key information (in production, use NLP/LLM)
        extracted = []

        for msg in messages:
            # Simple heuristic: save assistant messages that contain important keywords
            if msg["role"] == "assistant":
                important_keywords = [
                    "important",
                    "remember",
                    "note",
                    "key",
                    "critical",
                    "must",
                    "should",
                ]
                content_lower = msg["content"].lower()

                if any(keyword in content_lower for keyword in important_keywords):
                    # Save as memory
                    memory = await save_memory(
                        user_id,
                        f"From conversation: {msg['content'][:200]}",
                        importance=2,
                    )
                    extracted.append(memory)

        return {"status": "OK", "extracted": extracted, "count": len(extracted)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract memory: {str(e)}",
        )


@router.post("/context")
async def get_memory_context(authorization: str = Header(None), limit: int = 5):
    """Get memory context for AI - returns formatted context string"""
    user_id = get_user_id_from_token(authorization)

    try:
        memory = await get_user_memory(user_id, limit)

        if not memory:
            return {"status": "OK", "context": "", "memory_count": 0}

        # Format memory as context
        context_lines = ["User Context/Memory:"]
        for entry in memory:
            context_lines.append(f"- {entry['content']}")

        context = "\n".join(context_lines)

        return {"status": "OK", "context": context, "memory_count": len(memory)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory context: {str(e)}",
        )


@router.post("/auto-extract")
async def auto_extract_memory(conversation_id: int, authorization: str = Header(None)):
    """Automatically extract and save memory from conversation using LLM"""
    user_id = get_user_id_from_token(authorization)

    try:
        from openai import OpenAI
        import os

        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI client not configured",
            )

        client = OpenAI(api_key=OPENAI_API_KEY)

        # Get conversation messages
        messages = await get_recent_messages(conversation_id, limit=20)

        if not messages:
            return {
                "status": "OK",
                "message": "No messages to extract from",
                "extracted": [],
            }

        # Format messages for LLM
        conversation_text = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in messages]
        )

        # Use LLM to extract important information
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract the most important facts, preferences, and "
                        "information from this conversation that should be "
                        "remembered for future interactions. Return as a "
                        "bullet list."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Extract important information from this conversation:\n\n{conversation_text}",
                },
            ],
            temperature=0.5,
            max_tokens=500,
        )

        extracted_text = response.choices[0].message.content

        # Save as memory
        memory = await save_memory(user_id, extracted_text, importance=3)

        return {"status": "OK", "extracted": extracted_text, "memory": memory}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to auto-extract memory: {str(e)}",
        )
