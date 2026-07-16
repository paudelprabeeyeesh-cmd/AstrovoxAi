"""
Intelligence Engine API Router

Provides REST API endpoints for the intelligence engine:
- Process requests with full intelligence pipeline
- Get available models and tools
- View execution traces
- Access cost summaries and optimization suggestions
- Manage user preferences
"""

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

from .intelligence import IntelligenceCore
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

# Initialize intelligence core
intelligence_core = IntelligenceCore()


# Pydantic models
class ProcessRequestRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None
    optimize_for: str = "balanced"


class SetModelPreferenceRequest(BaseModel):
    model_name: str


@router.post("/process")
async def process_intelligent_request(
    request: ProcessRequestRequest,
    authorization: str = Header(None),
):
    """
    Process a request through the full intelligence pipeline.
    
    This endpoint uses the complete intelligence engine including:
    - Model orchestration
    - Intent detection
    - Context assembly
    - Reasoning pipeline
    - Tool execution
    - Response generation
    - Cost optimization
    - Execution tracing
    """
    user_id = get_user_id_from_token(authorization)
    
    try:
        result = await intelligence_core.process_request(
            user_message=request.message,
            user_id=user_id,
            conversation_id=request.conversation_id,
            context=request.context,
            user_preferences=request.user_preferences,
            optimize_for=request.optimize_for,
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Processing failed"),
            )
        
        return {
            "status": "OK",
            "result": result,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intelligence processing failed: {str(e)}",
        )


@router.get("/models")
async def list_models(authorization: str = Header(None)):
    """List all available AI models"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        models = intelligence_core.get_available_models()
        return {
            "status": "OK",
            "models": models,
            "count": len(models),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}",
        )


@router.get("/tools")
async def list_tools(authorization: str = Header(None)):
    """List all available tools"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        tools = intelligence_core.get_available_tools()
        return {
            "status": "OK",
            "tools": tools,
            "count": len(tools),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {str(e)}",
        )


@router.get("/trace/{request_id}")
async def get_execution_trace(
    request_id: str,
    authorization: str = Header(None),
):
    """Get execution trace for a specific request"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        trace = intelligence_core.get_execution_trace(request_id)
        if not trace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trace not found",
            )
        
        return {
            "status": "OK",
            "trace": trace,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trace: {str(e)}",
        )


@router.get("/costs")
async def get_cost_summary(authorization: str = Header(None)):
    """Get cost summary for the user"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        summary = intelligence_core.get_cost_summary(user_id)
        return {
            "status": "OK",
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost summary: {str(e)}",
        )


@router.get("/optimizations")
async def get_optimization_suggestions(authorization: str = Header(None)):
    """Get optimization suggestions based on usage patterns"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        suggestions = intelligence_core.get_optimization_suggestions(user_id)
        return {
            "status": "OK",
            "suggestions": suggestions,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimization suggestions: {str(e)}",
        )


@router.post("/preferences/model")
async def set_model_preference(
    request: SetModelPreferenceRequest,
    authorization: str = Header(None),
):
    """Set user's preferred AI model"""
    user_id = get_user_id_from_token(authorization)
    
    try:
        intelligence_core.set_user_model_preference(user_id, request.model_name)
        return {
            "status": "OK",
            "message": f"Model preference set to {request.model_name}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set model preference: {str(e)}",
        )


@router.get("/status")
async def get_intelligence_status():
    """Get intelligence engine status"""
    return {
        "status": "operational",
        "components": {
            "model_orchestrator": "active",
            "prompt_engine": "active",
            "reasoning_pipeline": "active",
            "tool_engine": "active",
            "planning_engine": "active",
            "response_generator": "active",
            "cost_optimizer": "active",
            "execution_tracer": "active",
            "reliability": "active",
        },
        "version": "2.0.0",
    }
