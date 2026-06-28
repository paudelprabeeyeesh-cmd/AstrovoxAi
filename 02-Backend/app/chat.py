from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional, List
import os

from openai import OpenAI

from .auth_utils import get_user_id_from_token
from .database import (
    create_conversation,
    get_conversations,
    get_conversation,
    update_conversation,
    create_message,
    get_messages,
    get_recent_messages,
    get_user_memory,
    save_memory,
    delete_conversation,
)

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Pydantic models
class CreateConversationRequest(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = "gpt-4"

class SendMessageRequest(BaseModel):
    conversation_id: int
    message: str
    model: Optional[str] = "gpt-4"

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str

@router.post("/conversations")
async def create_new_conversation(request: CreateConversationRequest, authorization: str = Header(None)):
    """Create a new conversation"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        conversation = await create_conversation(user_id, request.title, request.model)
        return {
            "status": "OK",
            "conversation": conversation
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )

@router.get("/conversations")
async def list_conversations(authorization: str = Header(None), limit: int = 50, offset: int = 0):
    """List user's conversations"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        conversations = await get_conversations(user_id, limit, offset)
        return {
            "status": "OK",
            "conversations": conversations,
            "count": len(conversations)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversations: {str(e)}"
        )

@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(conversation_id: int, authorization: str = Header(None)):
    """Get conversation details"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        conversation = await get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return {
            "status": "OK",
            "conversation": conversation
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation: {str(e)}"
        )

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, authorization: str = Header(None), limit: int = 100, offset: int = 0):
    """Get messages from a conversation"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        # Verify user owns this conversation
        conversation = await get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        messages = await get_messages(conversation_id, limit, offset)
        return {
            "status": "OK",
            "messages": messages,
            "count": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch messages: {str(e)}"
        )

@router.post("/message")
async def send_message(request: SendMessageRequest, authorization: str = Header(None)):
    """Send a message and get AI response"""
    user_id = get_user_id_from_token(authorization)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI client not configured"
        )
    
    try:
        # Verify user owns this conversation
        conversation = await get_conversation(request.conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Save user message
        user_msg = await create_message(
            request.conversation_id,
            user_id,
            "user",
            request.message
        )
        
        # Get conversation history
        messages = await get_recent_messages(request.conversation_id, limit=10)
        
        # Get user memory for context
        memory = await get_user_memory(user_id, limit=5)
        
        # Build context
        context_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
        
        # Add memory as system context
        memory_context = ""
        if memory:
            memory_context = "\n\nUser context/memory:\n" + "\n".join([m["content"] for m in memory[:3]])
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=request.model,
            messages=context_messages + [
                {"role": "user", "content": request.message}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        ai_response = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else None
        
        # Save AI message
        ai_msg = await create_message(
            request.conversation_id,
            user_id,
            "assistant",
            ai_response,
            model_used=request.model,
            tokens_used=tokens_used
        )
        
        # Update conversation
        await update_conversation(request.conversation_id, last_message_at="now()")
        
        # Save important info to memory
        if "important" in ai_response.lower() or "remember" in ai_response.lower():
            await save_memory(user_id, f"User asked: {request.message}\nAI responded: {ai_response[:200]}", importance=2)
        
        return {
            "status": "OK",
            "user_message": user_msg,
            "ai_message": ai_msg,
            "tokens_used": tokens_used
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )

@router.post("/conversations/{conversation_id}/title")
async def update_conversation_title(conversation_id: int, title: str, authorization: str = Header(None)):
    """Update conversation title"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        # Verify user owns this conversation
        conversation = await get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        updated = await update_conversation(conversation_id, title=title)
        return {
            "status": "OK",
            "conversation": updated
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation_route(conversation_id: int, authorization: str = Header(None)):
    """Delete a conversation"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        # Verify user owns this conversation
        conversation = await get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        await delete_conversation(conversation_id)
        
        return {
            "status": "OK",
            "message": "Conversation deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )
