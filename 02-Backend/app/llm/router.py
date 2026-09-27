from fastapi import APIRouter
from pydantic import BaseModel

from .service import LocalLLMService

router = APIRouter(prefix="/llm", tags=["llm"])
service = LocalLLMService()


class GenerateRequest(BaseModel):
    prompt: str
    system: str = ""
    max_new_tokens: int = 200
    temperature: float = 0.7
    top_k: Optional[int] = None


class GenerateResponse(BaseModel):
    text: str
    provider: str
    model: str
    tokens: int
    latency_ms: float
    confidence: float


@router.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    result = service.call_llm(
        prompt=request.prompt,
        system=request.system,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_k=request.top_k,
    )
    return GenerateResponse(**result)
