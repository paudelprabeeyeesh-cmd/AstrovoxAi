from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .core.prometheus_middleware import PrometheusMiddleware
from .core.cache_middleware import CacheMiddleware
import json
import logging
logger = logging.getLogger(__name__)
import os
import uuid
from contextlib import asynccontextmanager

import asyncio
import httpx

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles

from .ab_runner import get_variant
from .admin_panel import router as admin_router
from .ab_runner import record_result as record_ab_result
# REMOVED
# REMOVED
from .audit import log_action
from .auth import (get_current_user, login_user, refresh_access_token,
                   register_user, require_admin)
from .billing import (cancel_subscription, create_checkout_session,
                      create_premium_checkout_session, handle_stripe_webhook)
# REMOVED
# REMOVED
from .citations import create_citation, get_sources
from .comments import create_comment
from .conversations import (add_message, create_conversation, get_messages,
                            list_conversations, search_conversations)
from .core.budget import cost_circuit_breaker
from .core.context import ContextManager
from .core.grounding import ground_answer
from .core.guardrails import add_canary, sanitize_input, validate_output
from .core.llm import LLMClient
from .core.moderation import check_moderation
from .core.pii import redact_pii
from .core.tracing import get_prompt_hash, log_llm_call, start_trace
from .cost import count_tokens
from .database import init_db
from .feedback import create_feedback, list_feedback
from .integrations import (create_integration, delete_integration,
                           list_integrations)
from .interactions import create_interaction
from .knowledge import create_doc, delete_doc, list_docs, search_docs
from .memory import (create_memory, delete_memory, export_memories,
                     list_memories, search_memories, update_memory)
from .metrics import get_daily_cost, get_revenue, get_second_use_metric, get_usage
# REMOVED
from .profiles import get_profile, update_profile
from .prompts import PromptVersionManager
from .rate_limit import RateLimitMiddleware
from .referrals import create_referral, get_referral_stats
from .schedules import create_schedule, delete_schedule, list_schedules
from .schemas import (ConversationOut, ConversationSearchOut, FeedbackCreate,
                      FeedbackOut, KnowledgeDocCreate, KnowledgeDocOut,
                      MemoryCreate, MemoryOut, MemoryUpdate, MessageOut,
                      ScheduleCreate, ScheduleOut, SolveRequest, SolveResponse,
                       TemplateCreate, TemplateOut, ToolCreate, ToolOut,
                       UserProfileOut, WorkflowCreate, WorkflowOut, GenUIResponse)
from .templates import (create_template, delete_template, list_templates,
                        update_template)
from .tools import create_tool, delete_tool, list_tools
from .usage import record_usage
from .workflows import create_workflow, delete_workflow, list_workflows
from jose import JWTError, jwt
from .config import settings

print("[astrovox] imports complete", flush=True)


@asynccontextmanager
async def lifespan(app):
    print("[astrovox] lifespan startup", flush=True)
    yield
    print("[astrovox] lifespan shutdown", flush=True)


print("[astrovox] creating FastAPI app", flush=True)
app = FastAPI(title="AstrovoxAi", version="0.5.0", lifespan=lifespan)
print("[astrovox] FastAPI app created", flush=True)
security = HTTPBearer()

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CacheMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RateLimitMiddleware)
app.include_router(admin_router)

app.mount("/landing", StaticFiles(directory="../landing", html=True), name="landing")

_db_initialized = False


def _ensure_db():
    init_db()


def get_user_id(user_id: str = Depends(get_current_user)) -> str:
    return user_id


llm_client = LLMClient()
context_manager = ContextManager()
prompt_manager = PromptVersionManager()

import traceback

from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def _global_exception_handler(request, exc):
    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


@app.post("/genui", response_model=GenUIResponse)
async def genui(req: SolveRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    from app.core.router_v2 import get_router
    router = get_router()
    complexity = router.estimate_complexity(req.text)
    model = router.select_tier(complexity)
    from .core.llm import LLMClient
    llm = LLMClient()
    system = "You are a UI generator. Return JSON with type (chart, timeline, quiz, visualization) and data."
    prompt = f"Generate UI JSON for: {req.text}"
    try:
        result = llm.call_llm(prompt, system=system, timeout=30)
        text = result.get("text", "{}")
        import json, re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group(0)) if match else {"type": "visualization", "data": {}}
        if "type" not in data:
            data["type"] = "visualization"
        return GenUIResponse(type=data["type"], data=data.get("data", {}))
    except Exception as e:
        return GenUIResponse(type="visualization", data={"error": str(e)})

@app.post("/solve")
async def solve(req: SolveRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    with start_trace("solve", user_id, {"query_length": len(req.text)}):
        sanitized, injection_detected = sanitize_input(req.text)
        if injection_detected:
            log_action(
                user_id, "injection_attempt", json.dumps({"query": req.text[:100]})
            )

        moderated, flagged_category = check_moderation(sanitized)
        if moderated:
            return SolveResponse(
                model="moderation",
                cost_usd=0.0,
                cached=False,
                memories_used=[],
                conversation_id=None,
                message_id=None,
                confidence=0.0,
                refused=False,
                suggestions=[],
            )
        redacted = redact_pii(sanitized)
        prompt_with_canary = add_canary(redacted)

        memories = search_memories(user_id, req.text, limit=3)
        docs = search_docs(user_id, req.text, limit=3)

        context_parts = []
        if memories:
            memory_context = "\n".join([f"- {m.key}: {m.value}" for m in memories])
            context_parts.append(f"Memories:\n{memory_context}")
        if docs:
            doc_context = "\n".join(
                [f"[{d.title or 'doc'}]: {d.content[:500]}" for d in docs]
            )
            context_parts.append(f"Knowledge:\n{doc_context}")

        full_prompt = (
            "\n\n".join(context_parts + [f"User: {prompt_with_canary}"])
            if context_parts
            else prompt_with_canary
        )

        try:
            llm_result = llm_client.call_llm(full_prompt, timeout=30)
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

        add_message(conversation_id, "user", req.text)
        bot_msg = add_message(conversation_id, "assistant", grounded_response)

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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return "ok"


from fastapi.responses import HTMLResponse, JSONResponse, Response

@app.get("/terms", response_class=HTMLResponse)
async def terms():
    with open("../legal/terms.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    with open("../legal/privacy.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/dpa", response_class=HTMLResponse)
async def dpa():
    with open("../legal/dpa.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/auth/register")
async def register(data: RegisterRequest):
    user = register_user(data.email, data.password)
    return {"user": user}



@app.post("/auth/verify")
async def verify_email(token: str):
    from app.auth import verify_email_token
    result = verify_email_token(token)
    return result

@app.post("/auth/login")
async def login(data: LoginRequest):
    result = login_user(data.email, data.password)
    return result


@app.post("/auth/refresh")
async def refresh(data: RefreshRequest):
    result = refresh_access_token(data.refresh_token)
    return result


@app.get("/metrics")
async def prometheus_metrics(user_id: str = Depends(require_admin)):
    usage = get_usage(days=30)
    revenue = get_revenue(days=30)
    second_use = get_second_use_metric(days=7)
    return {**usage, **revenue, **second_use}


@app.get("/usage")
async def usage(user_id: str = Depends(get_user_id)):
    return get_usage(user_id=user_id)


@app.post("/memory", response_model=MemoryOut)
async def create_memory_endpoint(
    data: MemoryCreate, user_id: str = Depends(get_user_id)
):
    return create_memory(user_id, data)


@app.get("/memory", response_model=list[MemoryOut])
async def list_memories_endpoint(user_id: str = Depends(get_user_id)):
    return list_memories(user_id)


@app.get("/memory/search", response_model=list[MemoryOut])
async def search_memories_endpoint(user_id: str = Depends(get_user_id), q: str = ""):
    return search_memories(user_id, q)


@app.put("/memory/{memory_id}", response_model=MemoryOut)
async def update_memory_endpoint(
    memory_id: str, data: MemoryUpdate, user_id: str = Depends(get_user_id)
):
    try:
        return update_memory(memory_id, user_id, data)
    except ValueError:
        raise HTTPException(status_code=404, detail="Memory not found")


@app.delete("/memory/{memory_id}")
async def delete_memory_endpoint(memory_id: str, user_id: str = Depends(get_user_id)):
    delete_memory(memory_id, user_id)
    return {"ok": True}


@app.get("/memory/export")
async def export_memories_endpoint(user_id: str = Depends(get_user_id)):
    return export_memories(user_id)


@app.post("/conversations", response_model=ConversationOut)
async def create_conversation_endpoint(
    title: str = None, user_id: str = Depends(get_user_id)
):
    return create_conversation(user_id, title)


@app.get("/conversations", response_model=list[ConversationOut])
async def list_conversations_endpoint(user_id: str = Depends(get_user_id)):
    return list_conversations(user_id)


@app.get("/conversations/search", response_model=list[ConversationSearchOut])
async def search_conversations_endpoint(
    user_id: str = Depends(get_user_id), q: str = ""
):
    return search_conversations(user_id, q)


@app.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def get_messages_endpoint(conv_id: str, user_id: str = Depends(get_user_id)):
    try:
        return get_messages(conv_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")


@app.post("/templates", response_model=TemplateOut)
async def create_template_endpoint(
    data: TemplateCreate, user_id: str = Depends(get_user_id)
):
    return create_template(user_id, data)


@app.get("/templates", response_model=list[TemplateOut])
async def list_templates_endpoint(user_id: str = Depends(get_user_id)):
    return list_templates(user_id)


@app.put("/templates/{tpl_id}", response_model=TemplateOut)
async def update_template_endpoint(
    tpl_id: str, data: TemplateCreate, user_id: str = Depends(get_user_id)
):
    try:
        return update_template(tpl_id, user_id, data)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found")


@app.delete("/templates/{tpl_id}")
async def delete_template_endpoint(tpl_id: str, user_id: str = Depends(get_user_id)):
    delete_template(tpl_id, user_id)
    return {"ok": True}


@app.post("/schedules", response_model=ScheduleOut)
async def create_schedule_endpoint(
    data: ScheduleCreate, user_id: str = Depends(get_user_id)
):
    return create_schedule(user_id, data)


@app.get("/schedules", response_model=list[ScheduleOut])
async def list_schedules_endpoint(user_id: str = Depends(get_user_id)):
    return list_schedules(user_id)


@app.delete("/schedules/{schedule_id}")
async def delete_schedule_endpoint(
    schedule_id: str, user_id: str = Depends(get_user_id)
):
    delete_schedule(schedule_id, user_id)
    return {"ok": True}


@app.post("/knowledge", response_model=KnowledgeDocOut)
async def create_doc_endpoint(
    data: KnowledgeDocCreate, user_id: str = Depends(get_user_id)
):
    return create_doc(user_id, data)


@app.get("/knowledge", response_model=list[KnowledgeDocOut])
async def list_docs_endpoint(user_id: str = Depends(get_user_id)):
    return list_docs(user_id)


@app.get("/knowledge/search", response_model=list[KnowledgeDocOut])
async def search_docs_endpoint(user_id: str = Depends(get_user_id), q: str = ""):
    return search_docs(user_id, q)


@app.delete("/knowledge/{doc_id}")
async def delete_doc_endpoint(doc_id: str, user_id: str = Depends(get_user_id)):
    delete_doc(doc_id, user_id)
    return {"ok": True}


@app.get("/profile", response_model=UserProfileOut)
async def get_profile_endpoint(user_id: str = Depends(get_user_id)):
    return get_profile(user_id)


@app.post("/profile")
async def update_profile_endpoint(style_json: str, user_id: str = Depends(get_user_id)):
    update_profile(user_id, style_json)
    return {"ok": True}


@app.post("/workflows", response_model=WorkflowOut)
async def create_workflow_endpoint(
    data: WorkflowCreate, user_id: str = Depends(get_user_id)
):
    return create_workflow(user_id, data)


@app.get("/workflows", response_model=list[WorkflowOut])
async def list_workflows_endpoint(user_id: str = Depends(get_user_id)):
    return list_workflows(user_id)


@app.delete("/workflows/{wf_id}")
async def delete_workflow_endpoint(wf_id: str, user_id: str = Depends(get_user_id)):
    delete_workflow(wf_id, user_id)
    return {"ok": True}


@app.post("/tools", response_model=ToolOut)
async def create_tool_endpoint(data: ToolCreate, user_id: str = Depends(get_user_id)):
    return create_tool(user_id, data)


@app.get("/tools", response_model=list[ToolOut])
async def list_tools_endpoint(user_id: str = Depends(get_user_id)):
    return list_tools(user_id)


@app.delete("/tools/{tool_id}")
async def delete_tool_endpoint(tool_id: str, user_id: str = Depends(get_user_id)):
    delete_tool(tool_id, user_id)
    return {"ok": True}


@app.post("/feedback", response_model=FeedbackOut)
async def create_feedback_endpoint(
    data: FeedbackCreate, user_id: str = Depends(get_user_id)
):
    return create_feedback(user_id, data)


@app.get("/feedback", response_model=list[FeedbackOut])
async def list_feedback_endpoint(user_id: str = Depends(get_user_id)):
    return list_feedback(user_id)


@app.get("/cost/daily")
async def daily_cost(user_id: str = Depends(require_admin)):
    return get_daily_cost()


@app.post("/billing/checkout")
async def checkout(user_id: str = Depends(get_user_id)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        email = row["email"] if row else f"user{user_id}@example.com"
    session_url = create_checkout_session(user_id, email)
    return {"url": session_url}


@app.post("/billing/checkout/premium-action")
async def checkout_premium_action(user_id: str = Depends(get_user_id)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        email = row["email"] if row else f"user{user_id}@example.com"
    session_url = create_premium_checkout_session(user_id, email)
    return {"url": session_url}


@app.post("/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        result = handle_stripe_webhook(payload, sig_header)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/billing/cancel")
async def cancel_billing(user_id: str = Depends(get_user_id)):
    cancel_subscription(user_id)
    return {"ok": True}


@app.post("/referrals")
async def create_referral_endpoint(email: str, user_id: str = Depends(get_user_id)):
    return create_referral(user_id, email)


@app.get("/referrals")
async def get_referral_stats_endpoint(user_id: str = Depends(get_user_id)):
    return get_referral_stats(user_id)


@app.post("/integrations")
async def create_integration_endpoint(
    type: str, config: str, user_id: str = Depends(get_user_id)
):
    return create_integration(user_id, type, config)


@app.get("/integrations")
async def list_integrations_endpoint(user_id: str = Depends(get_user_id)):
    return list_integrations(user_id)


@app.delete("/integrations/{integration_id}")
async def delete_integration_endpoint(
    integration_id: str, user_id: str = Depends(get_user_id)
):
    delete_integration(integration_id, user_id)
    return {"ok": True}


@app.post("/removed")
async def create_post_endpoint(
    title: str, content: str, user_id: str = Depends(get_user_id)
):
    return create_post(user_id, title, content)


@app.get("/posts")
async def list_posts_endpoint(user_id: str = Depends(get_user_id)):
    return list_posts(user_id)


@app.post("/posts/{post_id}/comments")
async def create_comment_endpoint(
    post_id: str, content: str, user_id: str = Depends(get_user_id)
):
    return create_comment(post_id, user_id, content)


async def _authenticate_ws(websocket: WebSocket) -> str:
    token = websocket.query_params.get('token')
    if not token:
        try:
            first_message = await websocket.receive_text()
            try:
                data = json.loads(first_message)
                token = data.get('token')
            except Exception:
                pass
        except Exception:
            pass

    if not token:
        await websocket.close(code=4001, reason='Unauthorized')
        return None

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get('type') != 'access':
            await websocket.close(code=4001, reason='Unauthorized')
            return None
        return payload.get('sub')
    except JWTError:
        await websocket.close(code=4001, reason='Unauthorized')
        return None


# REMOVED# REMOVED# REMOVED# REMOVED# REMOVED# REMOVED# REMOVED# REMOVED# REMOVED# REMOVED@app.websocket("/ws/chat/{session_id}")
async def ws_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    user_id = await _authenticate_ws(websocket)
    if user_id is None:
        return
    try:
        while True:
            data = await websocket.receive_text()
            from app.core.router_v2 import get_router
            router = get_router()
            complexity = router.estimate_complexity(data)
            model = router.select_tier(complexity)
            prompt = data
            system = "You are a helpful assistant."
            async with httpx.AsyncClient(timeout=30) as client:
                provider_url = None
                api_key = None
                for p_name in ["groq", "gemini", "mistral", "openrouter", "huggingface"]:
                    key = os.getenv(f"{p_name.upper()}_API_KEY")
                    if key:
                        api_key = key
                        if p_name == "groq":
                            provider_url = "https://api.groq.com/openai/v1"
                        elif p_name == "gemini":
                            provider_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                        elif p_name == "mistral":
                            provider_url = "https://api.mistral.ai/v1"
                        elif p_name == "openrouter":
                            provider_url = "https://openrouter.ai/api/v1"
                        else:
                            provider_url = "https://router.huggingface.co/v1"
                        break
                if not provider_url:
                    await websocket.send_json({"error": "no_provider"})
                    continue
                payload = {
                    "model": model.model_id,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": True,
                }
                async with client.stream("POST", f"{provider_url}/chat/completions", json=payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=30) as response:
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            await websocket.send_text(chunk)
    except Exception as e:
        logger.warning(f"WebSocket chat error: {e}")
    finally:
        await websocket.close()


@app.websocket("/ws/voice/{session_id}")
async def ws_voice(websocket: WebSocket, session_id: str):
    await websocket.accept()
    user_id = await _authenticate_ws(websocket)
    if user_id is None:
        return
    audio_buffer = bytearray()
    try:
        while True:
            message = await websocket.receive()
            if "text" in message:
                text = message["text"]
                if text == "__END__":
                    transcript = f"[transcript for {session_id}]"
                    if audio_buffer:
                        transcript = f"[audio {len(audio_buffer)} bytes transcribed]"
                    audio_buffer.clear()
                    from app.core.router_v2 import get_router
                    router = get_router()
                    complexity = router.estimate_complexity(transcript)
                    model = router.select_tier(complexity)
                    await websocket.send_json({"transcript": transcript, "model": model.name})
                    async with httpx.AsyncClient(timeout=30) as client:
                        key = os.getenv("GROQ_API_KEY") or os.getenv("OPENROUTER_API_KEY")
                        base = "https://api.groq.com/openai/v1"
                        payload = {"model": model.model_id, "messages": [{"role": "user", "content": transcript}], "stream": True}
                        async with client.stream("POST", f"{base}/chat/completions", json=payload, headers={"Authorization": f"Bearer {key}"}, timeout=30) as response:
                            async for chunk in response.aiter_text():
                                if chunk.strip():
                                    await websocket.send_text(chunk)
                else:
                    audio_buffer.extend(text.encode("utf-8"))
            elif "bytes" in message:
                audio_buffer.extend(message["bytes"])
    except Exception as e:
        logger.warning(f"WebSocket voice error: {e}")
    finally:
        await websocket.close()
from .core.router_v2 import get_router
from .core.suggestions import SuggestionEngine


@app.post("/billing/portal")
async def billing_portal(user_id: str = Depends(get_user_id)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT stripe_customer_id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row or not row["stripe_customer_id"]:
            raise HTTPException(status_code=400, detail="No subscription found")
        session = stripe.billing_portal.Session.create(
            customer=row["stripe_customer_id"],
            return_url="https://astrovox.ai/settings",
        )
    return {"url": session.url}

@app.get("/ready")
async def ready():
    checks = {}
    try:
        from app.database import get_db
        with get_db() as conn:
            conn.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
    
    checks["redis"] = "not configured"
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            app.state.redis.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {e}"
    
    status = 200 if all(v == "ok" for v in checks.values()) else 503
    return JSONResponse(status_code=status, content=checks)

@app.get("/live")
async def live():
    return {"status": "alive"}


@app.get("/metrics")
async def prometheus_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
