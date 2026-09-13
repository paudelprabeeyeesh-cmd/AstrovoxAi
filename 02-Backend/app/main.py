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
from .billing import create_checkout_session, cancel_subscription
from .api_keys import create_api_key, validate_api_key, list_api_keys, delete_api_key
from .teams import create_team, add_member, list_teams, get_team
from .marketplace import create_prompt, list_prompts, get_prompt, increment_downloads
from .addons import create_addon, list_addons, get_addon_cost
from .audit import log_action, get_audit_logs
from .digest import send_daily_digest
from .subscriptions import get_plan_limits, create_team_checkout, create_embed_subscription
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
import uuid

app = FastAPI(title="AstrovoxAi", version="0.3.0")
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

@app.on_event("startup")
def startup():
    init_db()

def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    if not token.startswith("user-"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token.replace("user-", "")

@app.post("/solve")
async def solve(req: SolveRequest, user_id: str = Depends(get_user_id)):
    memories = search_memories(user_id, req.text, limit=3)
    memory_context = "\n".join([f"- {m.key}: {m.value}" for m in memories])
    
    docs = search_docs(user_id, req.text, limit=3)
    doc_context = "\n".join([f"[{d.title or 'doc'}]: {d.content[:500]}" for d in docs])
    
    context_parts = []
    if memory_context:
        context_parts.append(f"Memories:\n{memory_context}")
    if doc_context:
        context_parts.append(f"Knowledge:\n{doc_context}")
    
    full_prompt = "\n\n".join(context_parts + [f"User: {req.text}"]) if context_parts else req.text
    model = choose_model("simple")
    tokens = count_tokens(full_prompt, model=model)
    
    cache_key = f"{user_id}:{req.text}"
    result = cached(cache_key, lambda t: {"echo": t, "model": model, "tokens": tokens})
    confidence = 0.9 if tokens < 50 else 0.6
    answer = safe_answer(confidence)
    
    conversation_id = req.conversation_id
    if not conversation_id:
        conv = create_conversation(user_id, title=req.text[:50])
        conversation_id = conv.id
    
    add_message(conversation_id, "user", req.text)
    bot_msg = add_message(conversation_id, "assistant", result["echo"])
    
    record_usage(user_id, tokens, round(tokens * 0.00001, 6), model, result.get("cached", False))
    
    ab_variant = get_variant("model-comparison", user_id)
    if ab_variant:
        record_ab_result("model-comparison", ab_variant, "cost", tokens * 0.00001)
    
    sources = get_sources(str(uuid.uuid4()), user_id)
    citations = [create_citation(s, result["echo"][:200]) for s in sources]
    
    record_usage(user_id, tokens, round(tokens * 0.00001, 6), model, result.get("cached", False))
    
    ab_variant = get_variant("model-comparison", user_id)
    if ab_variant:
        record_ab_result("model-comparison", ab_variant, "cost", tokens * 0.00001)
    
    sources = get_sources(str(uuid.uuid4()), user_id)
    citations = [create_citation(s, result["echo"][:200]) for s in sources]
    
    return SolveResponse(
        result=result["echo"],
        model=result["model"],
        cost_usd=round(tokens * 0.00001, 6),
        cached=result.get("cached", False),
        memories_used=[m.key for m in memories],
        conversation_id=conversation_id,
        message_id=bot_msg.id
    )

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    usage = get_usage(days=30)
    revenue = get_revenue(days=30)
    return {**usage, **revenue}

@app.post("/ab/tests")
async def create_ab_test_endpoint(name: str, variants: str, traffic_split: str, user_id: str = Depends(get_user_id)):
    return {"test_id": create_ab_test(name, json.loads(variants), json.loads(traffic_split))}

@app.get("/citations")
async def get_citations(request_id: str = None, user_id: str = Depends(get_user_id)):
    sources = get_sources(request_id or str(uuid.uuid4()), user_id)
    return [create_citation(s, "") for s in sources]

@app.post("/ab/tests")
async def create_ab_test_endpoint(name: str, variants: str, traffic_split: str, user_id: str = Depends(get_user_id)):
    import json
    return {"test_id": create_ab_test(name, json.loads(variants), json.loads(traffic_split))}

@app.get("/citations")
async def get_citations(request_id: str = None, user_id: str = Depends(get_user_id)):
    sources = get_sources(request_id or str(uuid.uuid4()), user_id)
    return [create_citation(s, "") for s in sources]

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
async def daily_cost(user_id: str = Depends(get_user_id)):
    return get_daily_cost()

@app.post("/billing/checkout")
async def checkout(user_id: str = Depends(get_user_id)):
    session_url = create_checkout_session(user_id, f"user{user_id}@example.com")
    return {"url": session_url}

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

@app.get("/posts")
async def list_posts_endpoint():
    return list_posts()

@app.post("/posts/{post_id}/comments")
async def create_comment_endpoint(post_id: str, content: str, user_id: str = Depends(get_user_id)):
    return create_comment(post_id, user_id, content)

@app.get("/posts/{post_id}/comments")
async def list_comments_endpoint(post_id: str):
    return list_comments(post_id)

@app.post("/amas")
async def create_ama_endpoint(title: str, description: str, scheduled_at: str, user_id: str = Depends(get_user_id)):
    return create_ama(title, description, scheduled_at)

@app.get("/amas")
async def list_amas_endpoint():
    return list_amas()

@app.post("/case-studies")
async def create_case_study_endpoint(title: str, content: str, user_id: str = Depends(get_user_id)):
    return create_case_study(title, content, user_id)

@app.get("/case-studies")
async def list_case_studies_endpoint():
    return list_case_studies()

@app.post("/outreach")
async def create_outreach_endpoint(template_name: str, subject: str, body: str, recipient_email: str, user_id: str = Depends(get_user_id)):
    return create_outreach(user_id, template_name, subject, body, recipient_email)

@app.get("/outreach")
async def list_outreach_endpoint(user_id: str = Depends(get_user_id)):
    return list_outreach(user_id)

@app.post("/campaigns")
async def create_campaign_endpoint(name: str, platform: str, budget: float, start_date: str, end_date: str, user_id: str = Depends(get_user_id)):
    return create_ad_campaign(name, platform, budget, start_date, end_date)

@app.get("/campaigns")
async def list_campaigns_endpoint():
    return list_campaigns()

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

@app.post("/sso")
async def create_sso_endpoint(provider: str, config: str, user_id: str = Depends(get_user_id)):
    return create_sso_connection(user_id, provider, config)

@app.get("/sso")
async def list_sso_endpoint(user_id: str = Depends(get_user_id)):
    return list_sso_connections(user_id)

@app.get("/enterprise/audit")
async def enterprise_audit_endpoint(user_id: str = Depends(get_user_id)):
    return list_enterprise_audit_logs(user_id)

@app.post("/slas")
async def create_sla_endpoint(account_id: str, tier: str, uptime_guarantee: float, response_time_hours: int, user_id: str = Depends(get_user_id)):
    return create_sla(account_id, tier, uptime_guarantee, response_time_hours)

@app.get("/slas/{account_id}")
async def get_sla_endpoint(account_id: str, user_id: str = Depends(get_user_id)):
    return get_sla(account_id)

@app.post("/custom-models")
async def create_custom_model_endpoint(name: str, config: str, user_id: str = Depends(get_user_id)):
    return create_custom_model(user_id, name, config)

@app.get("/custom-models")
async def list_custom_models_endpoint(user_id: str = Depends(get_user_id)):
    return list_custom_models(user_id)

@app.post("/verticals")
async def create_vertical_endpoint(name: str, description: str, config: str, user_id: str = Depends(get_user_id)):
    return create_vertical(name, description, config)

@app.get("/verticals")
async def list_verticals_endpoint():
    return list_verticals()

@app.post("/regions")
async def create_region_endpoint(name: str, code: str, config: str, user_id: str = Depends(get_user_id)):
    return create_region(name, code, config)

@app.get("/regions")
async def list_regions_endpoint():
    return list_regions()

@app.post("/sdk-keys")
async def create_sdk_key_endpoint(name: str, user_id: str = Depends(get_user_id)):
    return create_sdk_key(user_id, name)

@app.get("/sdk-keys")
async def list_sdk_keys_endpoint(user_id: str = Depends(get_user_id)):
    return list_sdk_keys(user_id)

@app.post("/ma-targets")
async def create_ma_target_endpoint(name: str, description: str, valuation: float, user_id: str = Depends(get_user_id)):
    return create_ma_target(name, description, valuation)

@app.get("/ma-targets")
async def list_ma_targets_endpoint():
    return list_ma_targets()

@app.post("/ipo-metrics")
async def create_ipo_metric_endpoint(name: str, target: str, current: str, user_id: str = Depends(get_user_id)):
    return create_ipo_metric(name, target, current)

@app.get("/ipo-metrics")
async def list_ipo_metrics_endpoint():
    return list_ipo_metrics()
