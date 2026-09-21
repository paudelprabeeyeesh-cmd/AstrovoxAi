import logging
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..core.llm import LLMClient
from ..schemas import StructuredOutputRequest, StructuredOutputResponse, CitationRequest, CitationResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["structured"])


@router.post("/structured/generate", response_model=StructuredOutputResponse)
async def generate_structured(req: StructuredOutputRequest, user_id: str = Depends(require_verified_email)):
    try:
        client = LLMClient()
        schema_str = json.dumps(req.schema_json, indent=2)
        prompt = (
            f"{req.prompt}\n\n"
            f"Respond with valid JSON matching this schema:\n{schema_str}\n\n"
            f"Output only the JSON object, no additional text."
        )
        result = client.call_llm(prompt=prompt, timeout=60)
        text = result.get("text", "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise HTTPException(status_code=422, detail=f"Model did not return valid JSON: {text[:200]}")
        return StructuredOutputResponse(data=data, model=result.get("model", "unknown"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Structured generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/structured/citations", response_model=CitationResponse)
async def generate_citations(req: CitationRequest, user_id: str = Depends(require_verified_email)):
    try:
        citations = []
        for idx, source in enumerate(req.sources, start=1):
            citations.append({
                "id": idx,
                "source": source,
                "quote": req.text[:200],
                "confidence": 0.95,
            })
        return CitationResponse(citations=citations)
    except Exception as e:
        logger.error(f"Citation generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
