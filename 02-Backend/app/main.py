from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .core.prometheus_middleware import PrometheusMiddleware
from .core.structured_logging import configure_logging, StructuredLoggingMiddleware

from .core.cache_middleware import CacheMiddleware
import json
import logging
logger = logging.getLogger(__name__)
import os
import uuid
import time
from contextlib import asynccontextmanager

import asyncio
import httpx

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles

from .ab_runner import get_variant
from .admin_panel import router as admin_router
from .ab_runner import record_result as record_ab_result
# REMOVED
# REMOVED
from .audit import log_action
from .auth import (get_current_user, login_user, refresh_access_token,
                   register_user, require_admin, require_verified_email)
from .rbac import get_user_role, ROLE_PERMISSIONS, Role
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
from .context_builder import ContextBuilder
from .core.grounding import ground_answer
from .core.guardrails import add_canary, sanitize_input, validate_output
from .core.llm import LLMClient
from .core.moderation import check_moderation
from .core.pii import redact_pii
from .core.tracing import get_prompt_hash, init_tracing, log_llm_call, start_trace
from .cost import count_tokens
from .database import init_db
from .feedback import create_feedback, delete_feedback, list_feedback
from .compliance import delete_user_data, export_user_data, record_consent
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
from .schemas import (AnalyticsEventCreate, AnalyticsAggregateOut, RAGEvalCreate, ExperimentCreate, ExperimentOut, ExperimentResultOut, ConversationOut, ConversationSearchOut, FeedbackCreate,
                      FeedbackOut, KnowledgeDocCreate, KnowledgeDocOut,
                      MemoryCreate, MemoryOut, MemoryUpdate, MessageOut,
                      ScheduleCreate, ScheduleOut, SolveRequest, SolveResponse,
                       TemplateCreate, TemplateOut, ToolCreate, ToolOut,
                       UserProfileOut, WorkflowCreate, WorkflowOut, GenUIResponse, ConsentRecord,
                       SecurityScanPromptRequest, SecurityScanPromptResponse, SecurityScanSecretsRequest, SecurityScanSecretsResponse,
                       AuditLogRequest, AuditLogResponse, AuditLogsResponse,
                       ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyRevokeRequest)
from .templates import (create_template, delete_template, list_templates,
                        update_template)
from .tools import create_tool, delete_tool, list_tools
from .usage import record_usage
from .workflows import create_workflow, delete_workflow, list_workflows
from .security import PromptInjectionDetector, SecretScanner, InputSanitizer, EncryptionService
from .api_keys import create_api_key, revoke_api_key, list_api_keys, APIKey
from jose import JWTError, jwt
from .config import settings


import sentry_sdk
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
        environment=os.getenv("ENVIRONMENT", "development"),
    )

print("[astrovox] imports complete", flush=True)


@asynccontextmanager
async def lifespan(app):
    print("[astrovox] lifespan startup", flush=True)
    init_tracing(app=app)
    yield
    print("[astrovox] lifespan shutdown", flush=True)
    logger.info("Shutting down AstrovoxAI")

    try:
        from app.database import _pool
        if _pool is not None:
            _pool.closeall()
            logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

    try:
        logging.shutdown()
        logger.info("Logs flushed")
    except Exception as e:
        logger.error(f"Error flushing logs: {e}")

    try:
        if hasattr(app.state, "redis") and app.state.redis:
            await app.state.redis.close()
            logger.info("Redis connections closed")
    except Exception as e:
        logger.error(f"Error closing Redis connections: {e}")

    from datetime import datetime, timezone
    logger.info(f"Shutdown timestamp: {datetime.now(timezone.utc).isoformat()}")




class APIVersionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = "1.0.0"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.openai.com https://api.anthropic.com https://generativelanguage.googleapis.com https://api.groq.com https://openrouter.ai https://router.huggingface.co; "
        )
        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout: int = 30):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request, call_next):
        start_time = time.time()
        try:
            response = await asyncio.wait_for(call_next(request), timeout=self.timeout)
            elapsed = time.time() - start_time
            if elapsed > 5:
                logger.info(f"Slow request: {request.method} {request.url} took {elapsed:.2f}s")
            return response
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {request.method} {request.url} exceeded {self.timeout}s")
            return JSONResponse(
                status_code=504,
                content={"error": "Gateway Timeout", "detail": f"Request exceeded {self.timeout} seconds"},
            )


configure_logging()

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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CacheMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(APIVersionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TimeoutMiddleware)

app.include_router(admin_router)

app.mount("/landing", StaticFiles(directory="../landing", html=True), name="landing")

@app.options("/{path:path}")
async def options_handler(request: Request, path: str):
    return JSONResponse(status_code=204, content={})


_db_initialized = False


def _ensure_db():
    init_db()


def get_user_id(user_id: str = Depends(get_current_user)) -> str:
    return user_id


llm_client = LLMClient()
context_manager = ContextManager()
context_builder = ContextBuilder()
prompt_manager = PromptVersionManager()

import traceback

from fastapi.responses import JSONResponse, StreamingResponse


@app.exception_handler(Exception)
async def _global_exception_handler(request, exc):
    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


@app.post("/genui", response_model=GenUIResponse)
async def genui(req: SolveRequest, user_id: str = Depends(require_verified_email)):
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
async def solve(req: SolveRequest, user_id: str = Depends(require_verified_email)):
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

        full_prompt = context_builder.build_context(user_id, prompt_with_canary, max_tokens=128000)

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


@app.post("/solve/stream")
async def solve_stream(req: SolveRequest, user_id: str = Depends(require_verified_email)):
    _ensure_db()
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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get('/health/detailed')
async def health_detailed():
    from datetime import datetime, timezone
    checks = {}
    db_status = 'disconnected'
    redis_status = 'disconnected'
    try:
        from app.database import get_db
        with get_db() as conn:
            conn.execute('SELECT 1')
        db_status = 'connected'
    except Exception as e:
        db_status = f'disconnected ({e})'
    if hasattr(app.state, 'redis') and app.state.redis:
        try:
            app.state.redis.ping()
            redis_status = 'connected'
        except Exception as e:
            redis_status = f'disconnected ({e})'
    status = 'healthy' if db_status == 'connected' else 'degraded'
    return {
        'status': status,
        'database': db_status,
        'redis': redis_status,
        'version': '0.5.0',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }


@app.get("/healthz")
async def healthz():
    return "ok"


from fastapi.responses import HTMLResponse, JSONResponse, Response


@app.get("/version")
async def version():
    return {"version": "1.0.0", "name": "AstrovoxAI"}


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


class TrackEventRequest(BaseModel):
    event_name: str
    properties: dict = {}
    user_id: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@app.post("/auth/register")
async def register(data: RegisterRequest):
    """
    Register a new user.

    Example request:
        {
            "email": "user@example.com",
            "password": "securepassword123"
        }

    Example response:
        {
            "user": {
                "id": "uuid",
                "email": "user@example.com"
            }
        }
    """
    user = register_user(data.email, data.password)
    return {"user": user}



@app.post("/auth/verify")
async def verify_email(token: str):
    from app.auth import verify_email_token
    result = verify_email_token(token)
    return result


@app.post("/auth/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    from app.auth import forgot_password as forgot_password_func
    result = forgot_password_func(data.email)
    return result


@app.post("/auth/login")
async def login(data: LoginRequest):
    result = login_user(data.email, data.password)
    return result



@app.post("/auth/reset-password")
async def reset_password_endpoint(data: ResetPasswordRequest):
    from app.auth import reset_password as reset_password_func
    result = reset_password_func(data.token, data.new_password)
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



@app.get("/billing/current")
async def get_billing_current(user_id: str = Depends(get_user_id)):
    with get_db() as conn:
        user = conn.execute(
            "SELECT plan, stripe_customer_id FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        plan_name = user["plan"] or "free"
        limits = get_plan_limits(plan_name)
        usage_row = conn.execute(
            "SELECT SUM(tokens) as total_tokens FROM usage WHERE user_id = ? AND created_at >= datetime('now', '-30 days')",
            (user_id,)
        ).fetchone()
        current_usage = usage_row["total_tokens"] or 0 if usage_row else 0
        return {
            "plan": plan_name,
            "status": "active" if user["stripe_customer_id"] else "inactive",
            "current_usage": int(current_usage),
            "limit": limits["requests"],
        }


@app.get("/usage")
async def usage(user_id: str = Depends(get_user_id)):
    return get_usage(user_id=user_id)


@app.post("/memory", response_model=MemoryOut)
async def create_memory_endpoint(
    data: MemoryCreate, user_id: str = Depends(require_verified_email)
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
    memory_id: str, data: MemoryUpdate, user_id: str = Depends(require_verified_email)
):
    try:
        return update_memory(memory_id, user_id, data)
    except ValueError:
        raise HTTPException(status_code=404, detail="Memory not found")


@app.delete("/memory/{memory_id}")
async def delete_memory_endpoint(memory_id: str, user_id: str = Depends(require_verified_email)):
    try:
        delete_memory(memory_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True}


@app.get("/memory/export")
async def export_memories_endpoint(user_id: str = Depends(get_user_id)):
    return export_memories(user_id)


@app.post("/memory/classify", response_model=MemoryClassifyResponse)
async def classify_memory_endpoint(data: MemoryClassifyRequest, user_id: str = Depends(require_verified_email)):
    from app.memory_service import MemoryService
    service = MemoryService()
    with get_db() as conn:
        row = conn.execute("SELECT value FROM memories WHERE id = ? AND user_id = ?", (data.memory_id, user_id)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Memory not found")
        value = row["value"]
    memory_type, score = service.classify_memory(value)
    return MemoryClassifyResponse(memory_id=data.memory_id, category=memory_type.value, confidence=score)


@app.post("/conversations", response_model=ConversationOut)
async def create_conversation_endpoint(
    title: str = None, user_id: str = Depends(require_verified_email)
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
    data: TemplateCreate, user_id: str = Depends(require_verified_email)
):
    return create_template(user_id, data)


@app.get("/templates", response_model=list[TemplateOut])
async def list_templates_endpoint(user_id: str = Depends(get_user_id)):
    return list_templates(user_id)


@app.put("/templates/{tpl_id}", response_model=TemplateOut)
async def update_template_endpoint(
    tpl_id: str, data: TemplateCreate, user_id: str = Depends(require_verified_email)
):
    try:
        return update_template(tpl_id, user_id, data)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found")


@app.delete("/templates/{tpl_id}")
async def delete_template_endpoint(tpl_id: str, user_id: str = Depends(require_verified_email)):
    try:
        delete_template(tpl_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}


@app.post("/schedules", response_model=ScheduleOut)
async def create_schedule_endpoint(
    data: ScheduleCreate, user_id: str = Depends(require_verified_email)
):
    return create_schedule(user_id, data)


@app.get("/schedules", response_model=list[ScheduleOut])
async def list_schedules_endpoint(user_id: str = Depends(get_user_id)):
    return list_schedules(user_id)


@app.delete("/schedules/{schedule_id}")
async def delete_schedule_endpoint(
    schedule_id: str, user_id: str = Depends(require_verified_email)
):
    try:
        delete_schedule(schedule_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"ok": True}


@app.post("/knowledge", response_model=KnowledgeDocOut)
async def create_doc_endpoint(
    data: KnowledgeDocCreate, user_id: str = Depends(require_verified_email)
):
    return create_doc(user_id, data)


@app.get("/knowledge", response_model=list[KnowledgeDocOut])
async def list_docs_endpoint(user_id: str = Depends(get_user_id)):
    return list_docs(user_id)


@app.get("/knowledge/search", response_model=list[KnowledgeDocOut])
async def search_docs_endpoint(user_id: str = Depends(get_user_id), q: str = ""):
    return search_docs(user_id, q)


@app.delete("/knowledge/{doc_id}")
async def delete_doc_endpoint(doc_id: str, user_id: str = Depends(require_verified_email)):
    try:
        delete_doc(doc_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


@app.get("/profile", response_model=UserProfileOut)
async def get_profile_endpoint(user_id: str = Depends(get_user_id)):
    return get_profile(user_id)


@app.post("/profile")
async def update_profile_endpoint(style_json: str, user_id: str = Depends(require_verified_email)):
    update_profile(user_id, style_json)
    return {"ok": True}

@app.delete("/users/me")
async def delete_user_endpoint(user_id: str = Depends(get_user_id)):
    delete_user_data(user_id)
    return {"deleted": True}


@app.get("/users/me/export")
async def export_user_endpoint(user_id: str = Depends(get_user_id)):
    data = export_user_data(user_id)
    return JSONResponse(content=data)


@app.post("/users/me/consent")
async def record_consent_endpoint(
    data: ConsentRecord, user_id: str = Depends(get_user_id)
):
    record_consent(user_id, data.consent_type, data.granted)
    return {"recorded": True}



@app.post("/workflows", response_model=WorkflowOut)
async def create_workflow_endpoint(
    data: WorkflowCreate, user_id: str = Depends(require_verified_email)
):
    return create_workflow(user_id, data)


@app.get("/workflows", response_model=list[WorkflowOut])
async def list_workflows_endpoint(user_id: str = Depends(get_user_id)):
    return list_workflows(user_id)


@app.delete("/workflows/{wf_id}")
async def delete_workflow_endpoint(wf_id: str, user_id: str = Depends(require_verified_email)):
    try:
        delete_workflow(wf_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"ok": True}


@app.post("/tools", response_model=ToolOut)
async def create_tool_endpoint(data: ToolCreate, user_id: str = Depends(require_verified_email)):
    return create_tool(user_id, data)


@app.get("/tools", response_model=list[ToolOut])
async def list_tools_endpoint(user_id: str = Depends(get_user_id)):
    return list_tools(user_id)


@app.delete("/tools/{tool_id}")
async def delete_tool_endpoint(tool_id: str, user_id: str = Depends(require_verified_email)):
    try:
        delete_tool(tool_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"ok": True}


@app.post("/feedback", response_model=FeedbackOut)
async def create_feedback_endpoint(
    data: FeedbackCreate, user_id: str = Depends(require_verified_email)
):
    return create_feedback(user_id, data)


@app.get("/feedback", response_model=list[FeedbackOut])
async def list_feedback_endpoint(user_id: str = Depends(get_user_id)):
    return list_feedback(user_id)


@app.delete("/feedback/{fb_id}")
async def delete_feedback_endpoint(fb_id: str, user_id: str = Depends(require_verified_email)):
    try:
        delete_feedback(fb_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"ok": True}


@app.get("/cost/daily")
async def daily_cost(user_id: str = Depends(require_admin)):
    return get_daily_cost()


@app.post("/billing/checkout")
async def checkout(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        email = row["email"] if row else f"user{user_id}@example.com"
    session_url = create_checkout_session(user_id, email)
    return {"url": session_url}


@app.post("/billing/checkout/premium-action")
async def checkout_premium_action(user_id: str = Depends(require_verified_email)):
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
async def cancel_billing(user_id: str = Depends(require_verified_email)):
    cancel_subscription(user_id)
    return {"ok": True}



@app.get("/billing/invoices")
async def get_billing_invoices(user_id: str = Depends(get_user_id)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, amount, status, created_at FROM usage WHERE user_id = ? AND model = 'stripe_subscription' ORDER BY created_at DESC LIMIT 20",
            (user_id,)
        ).fetchall()
        return [
            {
                "id": r["id"],
                "amount": float(r["amount"]),
                "status": r["status"] or "paid",
                "date": r["created_at"],
            }
            for r in rows
        ]


@app.post("/referrals")
async def create_referral_endpoint(email: str, user_id: str = Depends(require_verified_email)):
    return create_referral(user_id, email)


@app.get("/referrals")
async def get_referral_stats_endpoint(user_id: str = Depends(get_user_id)):
    return get_referral_stats(user_id)


@app.post("/integrations")
async def create_integration_endpoint(
    type: str, config: str, user_id: str = Depends(require_verified_email)
):
    return create_integration(user_id, type, config)


@app.get("/integrations")
async def list_integrations_endpoint(user_id: str = Depends(get_user_id)):
    return list_integrations(user_id)


@app.delete("/integrations/{integration_id}")
async def delete_integration_endpoint(
    integration_id: str, user_id: str = Depends(require_verified_email)
):
    delete_integration(integration_id, user_id)
    return {"ok": True}


@app.post("/removed")
async def create_post_endpoint(
    title: str, content: str, user_id: str = Depends(require_verified_email)
):
    return create_post(user_id, title, content)


@app.get("/posts")
async def list_posts_endpoint(user_id: str = Depends(get_user_id)):
    return list_posts(user_id)


@app.post("/posts/{post_id}/comments")
async def create_comment_endpoint(
    post_id: str, content: str, user_id: str = Depends(require_verified_email)
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
async def billing_portal(user_id: str = Depends(require_verified_email)):
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




from .analytics import record_event, get_aggregate_metrics, get_top_models, get_cost_trend
from .rag_eval import create_evaluation, get_aggregate_metrics as get_rag_aggregate_metrics
from .experiments import create_experiment, assign_variant, record_win, get_winner, list_experiments



@app.post("/analytics/track")
async def track_analytics_endpoint(data: TrackEventRequest):
    _ensure_db()
    track_event(data.event_name, data.properties, data.user_id)
    return {"ok": True}


@app.post("/analytics/event")
async def record_analytics_event(
        data: AnalyticsEventCreate, user_id: str = Depends(require_verified_email)
    ):
    record_event(data.event_type, data.properties)
    return {"ok": True}


@app.get("/analytics/aggregate", response_model=AnalyticsAggregateOut)
async def analytics_aggregate(days: int = 7, user_id: str = Depends(require_admin)):
    metrics = get_aggregate_metrics(days=days)
    models = get_top_models(days=days)
    cost = get_cost_trend(days=days)
    return {**metrics, "top_models": models, "cost_trend": cost}


@app.post("/rag/eval")
async def rag_evaluate(
        data: RAGEvalCreate, user_id: str = Depends(require_verified_email)
    ):
    result = create_evaluation(
        query=data.query,
        retrieved_ids=data.retrieved_ids,
        golden_ids=data.golden_ids,
        faithfulness_score=data.faithfulness_score,
        metadata=data.metadata,
    )
    return result


@app.get("/rag/metrics")
async def rag_metrics(days: int = 7, user_id: str = Depends(require_admin)):
    return get_rag_aggregate_metrics(days=days)

from fastapi import UploadFile, File
from app.rag_engine import RAGEngine
from app.search import SearchEngine
from app.schemas import (
    DocumentOut, DocumentChunkOut, RAGSearchResult,
    RAGIngestResponse, RAGIngestRequest, RAGGithubRequest,
    SearchResultOut, MemoryClassifyRequest, MemoryClassifyResponse
)

rag_engine = RAGEngine()
search_engine = SearchEngine()

@app.post("/rag/ingest", response_model=RAGIngestResponse)
async def rag_ingest(file: UploadFile = File(...), user_id: str = Depends(require_verified_email)):
    _ensure_db()
    import tempfile
    suffix = "".join(c for c in file.filename if c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        if file.content_type == "application/pdf" or suffix.endswith(".pdf"):
            result = rag_engine.ingest_pdf(tmp_path, user_id)
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or suffix.endswith(".docx"):
            result = rag_engine.ingest_docx(tmp_path, user_id)
        elif suffix.endswith(".txt"):
            result = rag_engine.ingest_txt(tmp_path, user_id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        if not result:
            raise HTTPException(status_code=400, detail="Failed to ingest document")
        return RAGIngestResponse(doc_id=result[0]["doc_id"], chunks=result[0]["chunks"])
    finally:
        os.unlink(tmp_path)

@app.post("/rag/ingest/website", response_model=RAGIngestResponse)
async def rag_ingest_website(data: RAGIngestRequest, user_id: str = Depends(require_verified_email)):
    _ensure_db()
    result = rag_engine.ingest_website(data.url, user_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to ingest website")
    return RAGIngestResponse(doc_id=result[0]["doc_id"], chunks=result[0]["chunks"])

@app.post("/rag/ingest/github", response_model=RAGIngestResponse)
async def rag_ingest_github(data: RAGGithubRequest, user_id: str = Depends(require_verified_email)):
    _ensure_db()
    result = rag_engine.ingest_github_repo(data.repo_url, user_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to ingest GitHub repo")
    return RAGIngestResponse(doc_id=result[0]["doc_id"], chunks=result[0]["chunks"])

@app.post("/rag/search", response_model=list[RAGSearchResult])
async def rag_search(data: dict, user_id: str = Depends(get_user_id)):
    _ensure_db()
    query = data.get("query", "")
    top_k = data.get("top_k", 5)
    return rag_engine.search(query, user_id, top_k)

@app.get("/rag/documents", response_model=list[DocumentOut])
async def rag_list_documents(user_id: str = Depends(get_user_id)):
    _ensure_db()
    docs = list_documents(user_id)
    return [DocumentOut(**d) for d in docs]

@app.delete("/rag/documents/{doc_id}")
async def rag_delete_document(doc_id: str, user_id: str = Depends(require_verified_email)):
    _ensure_db()
    try:
        get_document(doc_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document_chunks(doc_id)
    if not delete_document(doc_id, user_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


@app.get("/search/semantic", response_model=list[SearchResultOut])
async def search_semantic_endpoint(user_id: str = Depends(get_user_id), q: str = "", top_k: int = 10):
    _ensure_db()
    return search_engine.semantic_search(q, user_id, top_k)


@app.get("/search/keyword", response_model=list[SearchResultOut])
async def search_keyword_endpoint(user_id: str = Depends(get_user_id), q: str = "", top_k: int = 10):
    _ensure_db()
    return search_engine.keyword_search(q, user_id, top_k)


@app.get("/search/hybrid", response_model=list[SearchResultOut])
async def search_hybrid_endpoint(user_id: str = Depends(get_user_id), q: str = "", top_k: int = 10, alpha: float = 0.7):
    _ensure_db()
    return search_engine.hybrid_search(q, user_id, top_k, alpha)


@app.post("/experiments", response_model=ExperimentOut)
async def create_experiment_endpoint(
        data: ExperimentCreate, user_id: str = Depends(require_verified_email)
    ):
    return create_experiment(
        name=data.name,
        hypothesis=data.hypothesis,
        variants=data.variants,
        traffic_split=data.traffic_split,
        owner_id=user_id,
    )


@app.post("/experiments/{experiment_id}/assign")
async def assign_experiment_variant(
        experiment_id: str, user_id: str = Depends(get_user_id)
    ):
    variant = assign_variant(experiment_id, user_id)
    return {"experiment_id": experiment_id, "variant": variant}


@app.post("/experiments/{experiment_id}/record")
async def record_experiment_win(
        experiment_id: str, variant: str, metric: str, value: float, user_id: str = Depends(get_user_id)
    ):
    record_win(experiment_id, variant, metric, value, user_id=user_id)
    return {"ok": True}


@app.get("/experiments/{experiment_id}/winner", response_model=ExperimentResultOut | None)
async def get_experiment_winner(
        experiment_id: str, metric: str = "conversion", user_id: str = Depends(require_admin)
    ):
    winner = get_winner(experiment_id, metric=metric)
    if not winner:
        return JSONResponse(status_code=404, content={"detail": "Not enough data"})
    return winner


@app.get("/experiments", response_model=list[ExperimentOut])
async def list_experiments_endpoint(user_id: str = Depends(get_user_id)):
    return list_experiments(user_id)


@app.get("/sentry-debug")
async def sentry_debug():
    import sentry_sdk
    sentry_sdk.capture_message("Sentry test message")
    return {"ok": True}


from fastapi.responses import FileResponse

@app.post("/files/upload")
async def upload_file_endpoint(file: UploadFile = File(...), user_id: str = Depends(require_verified_email)):
    _ensure_db()
    file_bytes = await file.read()
    url = storage_service.upload_file(file_bytes, file.filename, user_id, file.content_type or "application/octet-stream")
    return {"url": url, "filename": file.filename}

@app.get("/files")
async def list_files_endpoint(user_id: str = Depends(get_user_id)):
    _ensure_db()
    return storage_service.list_user_files(user_id)

@app.get("/files/{file_id}")
async def get_file_endpoint(file_id: str, user_id: str = Depends(get_user_id)):
    _ensure_db()
    return {"url": storage_service.get_file_url(file_id, user_id)}

@app.delete("/files/{file_id}")
async def delete_file_endpoint(file_id: str, user_id: str = Depends(require_verified_email)):
    _ensure_db()
    if not storage_service.delete_file(file_id, user_id):
        raise HTTPException(status_code=404, detail="File not found")
    return {"ok": True}

@app.get("/auth/me/permissions")
async def get_my_permissions(user_id: str = Depends(get_current_user)):
    role = get_user_role(user_id)
    permissions = ROLE_PERMISSIONS.get(Role(role), [])
    return {"role": role, "permissions": [p.value for p in permissions]}

@app.post("/admin/users/{user_id}/roles")
async def assign_role_endpoint(user_id: str, role_name: str, current_user: str = Depends(require_admin)):
    with get_db() as conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role_name, user_id))
        conn.commit()
    return {"ok": True}

@app.get("/admin/roles")
async def list_roles_endpoint(current_user: str = Depends(require_admin)):
    return [r.value for r in Role]

from fastapi import UploadFile, File
from pydantic import BaseModel


class TranscribeRequest(BaseModel):
    audio_url: Optional[str] = None


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "alloy"


class AnalyzeRequest(BaseModel):
    image_url: str
    prompt: str


class OCRRequest(BaseModel):
    image_url: str


class CodeExecuteRequest(BaseModel):
    language: str
    code: str
    timeout: int = 10


class BrowserNavigateRequest(BaseModel):
    url: str


class BrowserClickRequest(BaseModel):
    selector: str


class BrowserTypeRequest(BaseModel):
    selector: str
    text: str


class ImageGenerateRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"


class ImageEditRequest(BaseModel):
    image_url: str
    prompt: str


@app.post("/voice/transcribe")
async def voice_transcribe(file: UploadFile = File(...), user_id: str = Depends(get_user_id)):
    _ensure_db()
    from app.voice import VoiceService
    service = VoiceService()
    audio_bytes = await file.read()
    text = service.speech_to_text(audio_bytes, file.filename or "audio.wav")
    return {"text": text}


@app.post("/voice/synthesize")
async def voice_synthesize(data: SynthesizeRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    from app.voice import VoiceService
    service = VoiceService()
    audio_bytes = service.text_to_speech(data.text, data.voice)
    from fastapi.responses import Response
    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.post("/vision/analyze")
async def vision_analyze(data: AnalyzeRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    from app.vision import VisionService
    service = VisionService()
    result = service.analyze_image(data.image_url, data.prompt)
    return {"result": result}


@app.post("/vision/ocr")
async def vision_ocr(data: OCRRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    from app.vision import VisionService
    service = VisionService()
    result = service.extract_text_from_image(data.image_url)
    return {"text": result}


@app.post("/code/execute")
async def code_execute(data: CodeExecuteRequest, user_id: str = Depends(require_verified_email)):
    _ensure_db()
    from app.code_executor import CodeExecutor
    executor = CodeExecutor()
    if data.language == "python":
        result = executor.execute_python(data.code, data.timeout)
    elif data.language == "javascript":
        result = executor.execute_javascript(data.code, data.timeout)
    elif data.language == "bash":
        result = executor.execute_bash(data.code, data.timeout)
    else:
        raise HTTPException(status_code=400, detail="Unsupported language")
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "return_code": result.return_code,
        "timed_out": result.timed_out,
    }


@app.post("/browser/navigate")
async def browser_navigate(data: BrowserNavigateRequest, user_id: str = Depends(require_verified_email)):
    _ensure_db()
    from app.browser import BrowserAutomation
    browser = BrowserAutomation()
    try:
        content = await browser.navigate(data.url)
        return {"content": content}
    finally:
        await browser.close()


@app.post("/browser/screenshot")
async def browser_screenshot(user_id: str = Depends(require_verified_email)):
    _ensure_db()
    from app.browser import BrowserAutomation
    browser = BrowserAutomation()
    try:
        img_bytes = await browser.screenshot()
        from fastapi.responses import Response
        return Response(content=img_bytes, media_type="image/png")
    finally:
        await browser.close()


@app.post("/browser/click")
async def browser_click(data: BrowserClickRequest, user_id: str = Depends(require_verified_email)):
    _ensure_db()
    from app.browser import BrowserAutomation
    browser = BrowserAutomation()
    try:
        success = await browser.click(data.selector)
        return {"success": success}
    finally:
        await browser.close()


@app.post("/browser/type")
async def browser_type(data: BrowserTypeRequest, user_id: str = Depends(require_verified_email)):
    _ensure_db()
    from app.browser import BrowserAutomation
    browser = BrowserAutomation()
    try:
        success = await browser.type_text(data.selector, data.text)
        return {"success": success}
    finally:
        await browser.close()


@app.post("/images/generate")
async def image_generate(data: ImageGenerateRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    from app.image_gen import ImageGenerator
    generator = ImageGenerator()
    url = generator.generate_image(data.prompt, data.size)
    return {"url": url}


@app.post("/images/edit")
async def image_edit(data: ImageEditRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    from app.image_gen import ImageGenerator
    generator = ImageGenerator()
    url = generator.edit_image(data.image_url, data.prompt)
    return {"url": url}


injection_detector = PromptInjectionDetector()
secret_scanner = SecretScanner()
input_sanitizer = InputSanitizer()
encryption_service = EncryptionService()


@app.post("/security/scan-prompt", response_model=SecurityScanPromptResponse)
async def security_scan_prompt(data: SecurityScanPromptRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    injected = injection_detector.detect(data.prompt)
    return SecurityScanPromptResponse(injected=injected, confidence=1.0 if injected else 0.0)


@app.post("/security/scan-secrets", response_model=SecurityScanSecretsResponse)
async def security_scan_secrets(data: SecurityScanSecretsRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    findings = secret_scanner.scan(data.text)
    return SecurityScanSecretsResponse(secrets_found=len(findings), findings=findings)


@app.post("/audit/log", response_model=AuditLogResponse)
async def audit_log(data: AuditLogRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    from .audit import log_action
    log_action(user_id, data.action, data.resource, data.details)
    return AuditLogResponse(success=True, entry_id=str(uuid.uuid4()))


@app.get("/audit/logs", response_model=AuditLogsResponse)
async def audit_logs(user_id: str = Depends(get_user_id), limit: int = 100):
    _ensure_db()
    from .audit import get_audit_log
    logs = get_audit_log(user_id, limit)
    return AuditLogsResponse(logs=logs, total=len(logs))


@app.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_key(data: ApiKeyCreateRequest, user_id: str = Depends(get_user_id)):
    _ensure_db()
    key = create_api_key(user_id, data.name, data.scopes)
    return ApiKeyCreateResponse(
        id=key.id,
        name=key.name,
        key=key.key,
        scopes=key.scopes,
        created_at=key.created_at,
    )


@app.get("/api-keys")
async def list_keys(user_id: str = Depends(get_user_id)):
    _ensure_db()
    keys = list_api_keys(user_id)
    return {
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "scopes": k.scopes,
                "last_used": k.last_used,
                "created_at": k.created_at,
            }
            for k in keys
        ]
    }


@app.delete("/api-keys/{key_id}")
async def revoke_key(key_id: str, user_id: str = Depends(get_user_id)):
    _ensure_db()
    success = revoke_api_key(user_id, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"success": True}
