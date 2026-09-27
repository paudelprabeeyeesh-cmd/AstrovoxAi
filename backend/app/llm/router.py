"""FastAPI router for LLM endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .service import llm_service

router = APIRouter(prefix="/llm", tags=["llm"])


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Input prompt for generation")
    max_new_tokens: int = Field(default=200, ge=1, le=1024, description="Maximum number of tokens to generate")
    temperature: float = Field(default=0.8, ge=0.1, le=2.0, description="Sampling temperature")
    top_k: int = Field(default=50, ge=1, description="Top-k sampling parameter")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message for chat")
    max_new_tokens: int = Field(default=200, ge=1, le=1024, description="Maximum number of tokens to generate")
    temperature: float = Field(default=0.8, ge=0.1, le=2.0, description="Sampling temperature")
    top_k: int = Field(default=50, ge=1, description="Top-k sampling parameter")


class GenerateResponse(BaseModel):
    text: str
    prompt: str


class ChatResponse(BaseModel):
    response: str
    message: str


@router.post("/generate", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest):
    try:
        text = llm_service.generate(
            prompt=request.prompt,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_k=request.top_k,
        )
        return GenerateResponse(text=text, prompt=request.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        response = llm_service.chat(
            message=request.message,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_k=request.top_k,
        )
        return ChatResponse(response=response, message=request.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
