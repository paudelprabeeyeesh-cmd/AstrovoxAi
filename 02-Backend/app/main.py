from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from .cost import count_tokens
from .cache import cached
from .router import choose_model
from .fallback import safe_answer
from .database import init_db
from .schemas import SolveRequest, SolveResponse, MemoryCreate, MemoryUpdate, MemoryOut, ConversationOut, MessageOut, TemplateCreate, TemplateOut, ScheduleCreate, ScheduleOut, KnowledgeDocCreate, KnowledgeDocOut, UserProfileOut, WorkflowCreate, WorkflowOut, ToolCreate, ToolOut, FeedbackCreate, FeedbackOut, ConversationSearchOut
from .memory import create_memory, get_memory, list_memories, update_memory, delete_memory, search_memories, export_memories
from .conversations import create_conversation, get_conversation, list_conversations, search_conversations, add_message, get_messages
from .templates import create_template, get_template, list_templates, update_template, delete_template
from .schedules import create_schedule, get_schedule, list_schedules, delete_schedule
from .knowledge import create_doc, get_doc, list_docs, search_docs, delete_doc
from .profiles import get_profile, update_profile
from .workflows import create_workflow, get_workflow, list_workflows, delete_workflow
from .tools import create_tool, get_tool, list_tools, delete_tool
from .feedback import create_feedback, list_feedback
from .metrics import get_usage, get_daily_cost, get_revenue
from .billing import create_checkout_session, cancel_subscription, handle_stripe_webhook
from .api_keys import create_api_key, validate_api_key, list_api_keys, delete_api_key
from .teams import create_team, add_member, list_teams, get_team
from .marketplace import create_prompt, list_prompts, get_prompt, increment_downloads
from .addons import create_addon, list_addons, get_addon_cost
from .audit import log_action, get_audit_logs
from .digest import send_daily_digest
from .subscriptions import get_plan_limits, create_team_checkout, create_embed_subscription
from .rate_limit import RateLimitMiddleware
from .ab_runner import create_ab_test, get_variant, record_result as record_ab_result
from .citations import get_sources, create_citation
from .usage import record_usage
from .referrals import create_referral, track_signup, get_referral_stats
from .integrations import create_integration, list_integrations, delete_integration
from .posts import create_post, list_posts
from .comments import create_comment, list_comments
from .amas import create_ama, list_amas
from .case_studies import create_case_study, list_case_studies
from .outreach import create_outreach, list_outreach
from .campaigns import create_ad_campaign, list_campaigns
from .affiliates import create_affiliate, list_affiliates, track_conversion
from .api_keys import create_api_key, validate_api_key, list_api_keys, delete_api_key
from .teams import create_team, add_member, list_teams, get_team
from .marketplace import create_prompt, list_prompts, get_prompt, increment_downloads
from .addons import create_addon, list_addons, get_addon_cost
from .audit import log_action, get_audit_logs
from .core.llm import LLMClient
from .core.guardrails import sanitize_input, validate_output, add_canary
from .core.pii import redact_pii, restore_pii
from .core.moderation import check_moderation
from .core.grounding import ground_answer
from .core.tracing import start_trace, log_llm_call, get_prompt_hash
from .core.context import ContextManager
from .prompts import PromptVersionManager
from .core.ratelimit import rate_limiter
from .core.budget import cost_circuit_breaker
from .core.circuit_breaker import CircuitBreaker
from .auth import get_current_user, require_admin, register_user, login_user, refresh_access_token
import os
import logging
import uuid
import json
import time

logger = logging.getLogger(__name__)

app = FastAPI(title="AstrovoxAi", version="0.5.0")
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://astrovox.ai"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(RateLimitMiddleware)

@app.on_event("startup")
def startup():
    init_db()

def get_user_id(user_id: str = Depends(get_current_user)) -> str:
    return user_id

llm_client = LLMClient()
context_manager = ContextManager()
prompt_manager = PromptVersionManager()

@app.post("/solve")
async def solve(req: SolveRequest, user_id: str = Depends(get_user_id)):
    with start_trace("solve", user_id, {"query_length": len(req.text)}):
        sanitized, injection_detected = sanitize_input(req.text)
        if injection_detected:
            log_action(user_id, "injection_attempt", json.dumps({"query": req.text[:100]}))
        
        moderated, flagged_category = check_moderation(sanitized)
        if moderated:
            return SolveResponse(
                result="I cannot process this request.",
                model="moderation",
                cost_usd=0.0,
                cached=False,
                memories_used=[],
                conversation_id=None,
                message_id=None,
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
            doc_context = "\n".join([f"[{d.title or 'doc'}]: {d.content[:500]}" for d in docs])
            context_parts.append(f"Knowledge:\n{doc_context}")
        
        full_prompt = "\n\n".join(context_parts + [f"User: {prompt_with_canary}"]) if context_parts else prompt_with_canary
        
        try:
            llm_result = llm_client.call_llm(full_prompt)
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
        )

@app.get("/health")
async def health():
    return {"status": "ok"}

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

@app.post("/auth/login")
async def login(data: LoginRequest):
    result = login_user(data.email, data.password)
    return result

@app.post("/auth/refresh")
async def refresh(data: RefreshRequest):
    result = refresh_access_token(data.refresh_token)
    return result

@app.get("/metrics")
async def metrics(user_id: str = Depends(require_admin)):
    usage = get_usage(days=30)
    revenue = get_revenue(days=30)
    return {**usage, **revenue}

@app.get("/usage")
async def usage(user_id: str = Depends(get_user_id)):
    return get_usage(user_id=user_id)

@app.post("/memory", response_model=MemoryOut)
async def create_memory_endpoint(data: MemoryCreate, user_id: str = Depends(get_user_id)):
    return create_memory(user_id, data)

@app.get("/memory", response_model=list[MemoryOut])
async def list_memories_endpoint(user_id: str = Depends(get_user_id)):
    return list_memories(user_id)

@app.get("/memory/search", response_model=list[MemoryOut])
async def search_memories_endpoint(user_id: str = Depends(get_user_id), q: str = ""):
    return search_memories(user_id, q)

@app.put("/memory/{memory_id}", response_model=MemoryOut)
async def update_memory_endpoint(memory_id: str, data: MemoryUpdate, user_id: str = Depends(get_user_id)):
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
async def create_conversation_endpoint(title: str = None, user_id: str = Depends(get_user_id)):
    return create_conversation(user_id, title)

@app.get("/conversations", response_model=list[ConversationOut])
async def list_conversations_endpoint(user_id: str = Depends(get_user_id)):
    return list_conversations(user_id)

@app.get("/conversations/search", response_model=list[ConversationSearchOut])
async def search_conversations_endpoint(user_id: str = Depends(get_user_id), q: str = ""):
    return search_conversations(user_id, q)

@app.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def get_messages_endpoint(conv_id: str, user_id: str = Depends(get_user_id)):
    try:
        return get_messages(conv_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")

@app.post("/templates", response_model=TemplateOut)
async def create_template_endpoint(data: TemplateCreate, user_id: str = Depends(get_user_id)):
    return create_template(user_id, data)

@app.get("/templates", response_model=list[TemplateOut])
async def list_templates_endpoint(user_id: str = Depends(get_user_id)):
    return list_templates(user_id)

@app.put("/templates/{tpl_id}", response_model=TemplateOut)
async def update_template_endpoint(tpl_id: str, data: TemplateCreate, user_id: str = Depends(get_user_id)):
    try:
        return update_template(tpl_id, user_id, data)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found")

@app.delete("/templates/{tpl_id}")
async def delete_template_endpoint(tpl_id: str, user_id: str = Depends(get_user_id)):
    delete_template(tpl_id, user_id)
    return {"ok": True}

@app.post("/schedules", response_model=ScheduleOut)
async def create_schedule_endpoint(data: ScheduleCreate, user_id: str = Depends(get_user_id)):
    return create_schedule(user_id, data)

@app.get("/schedules", response_model=list[ScheduleOut])
async def list_schedules_endpoint(user_id: str = Depends(get_user_id)):
    return list_schedules(user_id)

@app.delete("/schedules/{schedule_id}")
async def delete_schedule_endpoint(schedule_id: str, user_id: str = Depends(get_user_id)):
    delete_schedule(schedule_id, user_id)
    return {"ok": True}

@app.post("/knowledge", response_model=KnowledgeDocOut)
async def create_doc_endpoint(data: KnowledgeDocCreate, user_id: str = Depends(get_user_id)):
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
async def create_workflow_endpoint(data: WorkflowCreate, user_id: str = Depends(get_user_id)):
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
async def create_feedback_endpoint(data: FeedbackCreate, user_id: str = Depends(get_user_id)):
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
        row = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
        email = row["email"] if row else f"user{user_id}@example.com"
    session_url = create_checkout_session(user_id, email)
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
async def create_integration_endpoint(type: str, config: str, user_id: str = Depends(get_user_id)):
    return create_integration(user_id, type, config)

@app.get("/integrations")
async def list_integrations_endpoint(user_id: str = Depends(get_user_id)):
    return list_integrations(user_id)

@app.delete("/integrations/{integration_id}")
async def delete_integration_endpoint(integration_id: str, user_id: str = Depends(get_user_id)):
    delete_integration(integration_id, user_id)
    return {"ok": True}

@app.post("/posts")
async def create_post_endpoint(title: str, content: str, user_id: str = Depends(get_user_id)):
    return create_post(title, content, user_id)

@app.post("/posts/{post_id}/comments")
async def create_comment_endpoint(post_id: str, content: str, user_id: str = Depends(get_user_id)):
    return create_comment(post_id, user_id, content)

@app.post("/amas")
async def create_ama_endpoint(title: str, description: str, scheduled_at: str, user_id: str = Depends(get_user_id)):
    return create_ama(title, description, scheduled_at)

@app.post("/campaigns")
async def create_campaign_endpoint(name: str, platform: str, budget: float, start_date: str, end_date: str, user_id: str = Depends(get_user_id)):
    return create_ad_campaign(name, platform, budget, start_date, end_date)

@app.post("/affiliates")
async def create_affiliate_endpoint(name: str, email: str, user_id: str = Depends(get_user_id)):
    return create_affiliate(user_id, name, email)

@app.get("/affiliates")
async def list_affiliates_endpoint():
    return list_affiliates()

@app.post("/enterprise/accounts")
async def create_enterprise_account_endpoint(company: str, contact_email: str, user_id: str = Depends(get_user_id)):
    return create_enterprise_account(company, contact_email)

@app.get("/enterprise/accounts")
async def list_enterprise_accounts_endpoint():
    return list_enterprise_accounts()
