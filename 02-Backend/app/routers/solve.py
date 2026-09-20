import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..core.grounding import ground_answer
from ..core.guardrails import add_canary, validate_output, sanitize_input
from ..core.moderation import check_moderation
from ..core.pii import redact_pii
from ..core.tracing import start_trace, get_prompt_hash, log_llm_call
from ..cost import count_tokens
from ..schemas import SolveRequest, SolveResponse
from ..auth import require_verified_email
from ..circuit_breaker import llm_circuit_breaker
from ..retry import retry_with_backoff
from ..database import get_db
from ..memory import search_memories
from ..knowledge import search_docs
from ..interactions import create_interaction
from ..usage import record_usage
from ..ab_runner import get_variant, record_result as record_ab_result
from ..core.suggestions import SuggestionEngine
from ..citations import create_citation, get_sources
from ..core.budget import cost_circuit_breaker
from ..audit import log_action
from ..conversations import add_message, create_conversation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["solve"])


@router.post("/solve", response_model=SolveResponse)
async def solve(req: SolveRequest, user_id: str = Depends(require_verified_email)):
    from ..main import llm_client, context_builder
    from ..database import init_db

    init_db()

    with start_trace("solve", user_id, {"query_length": len(req.text)}):
        sanitized, injection_detected = sanitize_input(req.text)
        if injection_detected:
            log_action(
                user_id, "injection_attempt", json.dumps({"query": req.text[:100]})
            )

        moderated, flagged_category = check_moderation(sanitized)
        if moderated:
            return SolveResponse(
                result="",
                provider="moderation",
                model="moderation",
                cost_usd=0.0,
                cached=False,
                memories_used=[],
                conversation_id=None,
                message_id=None,
                confidence=0.0,
                refused=True,
                suggestions=[],
            )
        redacted = redact_pii(sanitized)
        prompt_with_canary = add_canary(redacted)

        memories = search_memories(user_id, req.text, limit=3)
        docs = search_docs(user_id, req.text, limit=3)

        full_prompt = context_builder.build_context(user_id, prompt_with_canary, max_tokens=128000)

        try:
            llm_result = llm_circuit_breaker.call(
                retry_with_backoff(llm_client.call_llm, max_retries=3, base_delay=1),
                full_prompt,
                timeout=30,
            )
            response_text = llm_result.get("text", "")
            provider = llm_result.get("provider", "unknown")
            model = llm_result.get("model", "unknown")
            tokens = llm_result.get("tokens", count_tokens(full_prompt, model=model))
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            response_text = "I encountered an error processing your request."
            provider = "error"
            model = "error"
            tokens = 0

        cleaned_response, canary_detected = validate_output(response_text)

        grounded_response, refused, confidence = ground_answer(
            cleaned_response, docs, req.text
        )

        conversation_id = req.conversation_id
        if not conversation_id:
            conv = create_conversation(user_id, title=req.text[:50])
            conversation_id = conv.id

        add_message(conversation_id, "user", req.text, user_id)
        bot_msg = add_message(conversation_id, "assistant", grounded_response, user_id)

        tokens = count_tokens(full_prompt, model=model)
        cost = round(tokens * 0.00001, 6)
        record_usage(user_id, tokens, cost, model, False)

        ab_variant = get_variant("model-comparison", user_id)
        if ab_variant:
            record_ab_result("model-comparison", ab_variant, "cost", cost)

        sources = get_sources(str(uuid.uuid4()), user_id)
        citations = [create_citation(s, grounded_response[:200]) for s in sources]

        prompt_hash = get_prompt_hash(full_prompt)
        log_llm_call(
            prompt_hash=prompt_hash,
            model=model,
            tokens=tokens,
            cost=cost,
            latency_ms=0,
            cached=False,
        )

        cost_circuit_breaker.record_cost(user_id, cost)

        create_interaction(
            user_id=user_id,
            prompt=req.text,
            response=grounded_response,
            model=model,
            tokens=tokens,
            cost=cost,
            latency_ms=0,
        )
        suggestion_engine = SuggestionEngine()
        suggestions = suggestion_engine.generate(user_id, [m.key for m in memories])

        return SolveResponse(
            result=grounded_response,
            provider=provider,
            model=model,
            cost_usd=cost,
            cached=False,
            memories_used=[m.key for m in memories],
            conversation_id=conversation_id,
            message_id=bot_msg.id,
            confidence=confidence,
            refused=refused,
            suggestions=suggestions,
        )


@router.post("/solve/stream")
async def solve_stream(req: SolveRequest, user_id: str = Depends(require_verified_email)):
    from ..main import llm_client, context_builder
    from ..database import init_db

    init_db()
    sanitized, injection_detected = sanitize_input(req.text)
    if injection_detected:
        log_action(
            user_id, "injection_attempt", json.dumps({"query": req.text[:100]})
        )

    moderated, flagged_category = check_moderation(sanitized)
    if moderated:
        payload = json.dumps({
            "token": "",
            "error": "moderated",
            "flagged_category": flagged_category,
        })
        async def _gen():
            yield f"data: {payload}\n\n"
            yield f"data: [DONE]\n\n"
        return StreamingResponse(_gen(), media_type="text/event-stream")

    redacted = redact_pii(sanitized)
    prompt_with_canary = add_canary(redacted)

    memories = search_memories(user_id, req.text, limit=3)
    docs = search_docs(user_id, req.text, limit=3)

    full_prompt = context_builder.build_context(user_id, prompt_with_canary, max_tokens=128000)

    async def event_generator():
        try:
            async for item in llm_client.stream_llm(full_prompt, timeout=60):
                token = item.get("token", "")
                provider = item.get("provider", "unknown")
                model = item.get("model", "unknown")
                payload = json.dumps({
                    "token": token,
                    "provider": provider,
                    "model": model,
                })
                yield f"data: {payload}\n\n"
        except Exception as e:
            logger.error(f"Streaming LLM call failed: {e}")
            payload = json.dumps({"token": "", "error": str(e)})
            yield f"data: {payload}\n\n"
        finally:
            yield f"data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
