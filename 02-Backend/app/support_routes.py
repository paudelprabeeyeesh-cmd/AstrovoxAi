from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from realtime import Optional as RealtimeOptional

from app.support_services import cx_service

router = APIRouter(prefix="/support", tags=["support"])


# ============================================================================
# Help Center
# ============================================================================

class ArticleCreateRequest(BaseModel):
    slug: str
    title: str
    content: str
    category: str
    tags: List[str] = []


class ArticleResponse(BaseModel):
    id: str
    slug: str
    title: str
    content: str
    category: str
    tags: List[str]
    views: int
    helpful_count: int
    not_helpful_count: int
    created_at: str
    updated_at: str


@router.post("/articles")
async def create_article(request: ArticleCreateRequest, authorization: str = Header(None)):
    article = cx_service.create_article(request.slug, request.title, request.content, request.category, request.tags)
    return {"status": "OK", "article": _article_to_dict(article)}


@router.get("/articles")
async def list_articles(category: str = None):
    articles = cx_service.list_articles(category)
    return {"status": "OK", "articles": [_article_to_dict(a) for a in articles]}


@router.get("/articles/search")
async def search_articles(q: str):
    articles = cx_service.search_articles(q)
    return {"status": "OK", "articles": [_article_to_dict(a) for a in articles]}


@router.get("/articles/{article_id}")
async def get_article(article_id: str):
    article = cx_service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    cx_service.increment_article_views(article_id)
    return {"status": "OK", "article": _article_to_dict(article)}


@router.post("/articles/{article_id}/feedback")
async def article_feedback(article_id: str, helpful: bool):
    cx_service.mark_article_helpful(article_id, helpful)
    return {"status": "OK"}


def _article_to_dict(article) -> Dict[str, Any]:
    return {
        "id": article.id,
        "slug": article.slug,
        "title": article.title,
        "content": article.content,
        "category": article.category,
        "tags": article.tags,
        "views": article.views,
        "helpful_count": article.helpful_count,
        "not_helpful_count": article.not_helpful_count,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }


# ============================================================================
# Tutorials
# ============================================================================

class TutorialCreateRequest(BaseModel):
    title: str
    description: str
    steps: List[Dict[str, Any]]
    difficulty: str = "beginner"
    estimated_time: int = 5


class TutorialResponse(BaseModel):
    id: str
    title: str
    description: str
    steps: List[Dict[str, Any]]
    difficulty: str
    estimated_time: int
    created_at: str
    updated_at: str


@router.post("/tutorials")
async def create_tutorial(request: TutorialCreateRequest):
    tutorial = cx_service.create_tutorial(request.title, request.description, request.steps, request.difficulty, request.estimated_time)
    return {"status": "OK", "tutorial": _tutorial_to_dict(tutorial)}


@router.get("/tutorials")
async def list_tutorials(difficulty: str = None):
    tutorials = cx_service.list_tutorials(difficulty)
    return {"status": "OK", "tutorials": [_tutorial_to_dict(t) for t in tutorials]}


@router.get("/tutorials/{tutorial_id}")
async def get_tutorial(tutorial_id: str):
    tutorial = cx_service.get_tutorial(tutorial_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    return {"status": "OK", "tutorial": _tutorial_to_dict(tutorial)}


@router.post("/tutorials/{tutorial_id}/start")
async def start_tutorial(tutorial_id: str, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    progress = cx_service.start_tutorial(user_id, tutorial_id)
    return {"status": "OK", "progress": _progress_to_dict(progress)}


@router.post("/tutorials/{tutorial_id}/progress")
async def update_tutorial_progress(tutorial_id: str, current_step: int, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    progress = cx_service.update_tutorial_progress(user_id, tutorial_id, current_step)
    if not progress:
        raise HTTPException(status_code=404, detail="Tutorial progress not found")
    return {"status": "OK", "progress": _progress_to_dict(progress)}


@router.get("/tutorials/progress")
async def get_tutorial_progress(authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    progress_list = cx_service.get_user_tutorial_progress(user_id)
    return {"status": "OK", "progress": [_progress_to_dict(p) for p in progress_list]}


def _tutorial_to_dict(tutorial) -> Dict[str, Any]:
    return {
        "id": tutorial.id,
        "title": tutorial.title,
        "description": tutorial.description,
        "steps": tutorial.steps,
        "difficulty": tutorial.difficulty,
        "estimated_time": tutorial.estimated_time,
        "created_at": tutorial.created_at,
        "updated_at": tutorial.updated_at,
    }


def _progress_to_dict(progress) -> Dict[str, Any]:
    return {
        "id": progress.id,
        "user_id": progress.user_id,
        "tutorial_id": progress.tutorial_id,
        "current_step": progress.current_step,
        "completed": progress.completed,
        "started_at": progress.started_at,
        "completed_at": progress.completed_at,
    }


# ============================================================================
# Feedback
# ============================================================================

class FeedbackRequest(BaseModel):
    type: str
    rating: Optional[int] = None
    comment: Optional[str] = None
    page_url: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    feedback = cx_service.submit_feedback(user_id, request.type, request.rating, request.comment, request.page_url)
    return {"status": "OK", "feedback": _feedback_to_dict(feedback)}


@router.get("/feedback")
async def list_feedback(feedback_type: str = None):
    feedbacks = cx_service.list_feedback(feedback_type)
    return {"status": "OK", "feedback": [_feedback_to_dict(f) for f in feedbacks]}


def _feedback_to_dict(feedback) -> Dict[str, Any]:
    return {
        "id": feedback.id,
        "user_id": feedback.user_id,
        "type": feedback.type,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "page_url": feedback.page_url,
        "created_at": feedback.created_at,
    }


# ============================================================================
# NPS
# ============================================================================

class NpsRequest(BaseModel):
    score: int
    comment: Optional[str] = None
    survey_type: str = "periodic"


@router.post("/nps")
async def submit_nps(request: NpsRequest, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    survey = cx_service.submit_nps(user_id, request.score, request.comment, request.survey_type)
    return {"status": "OK", "survey": _nps_to_dict(survey)}


@router.get("/nps/stats")
async def get_nps_stats():
    stats = cx_service.get_nps_stats()
    return {"status": "OK", "stats": stats}


def _nps_to_dict(survey) -> Dict[str, Any]:
    return {
        "id": survey.id,
        "user_id": survey.user_id,
        "score": survey.score,
        "comment": survey.comment,
        "survey_type": survey.survey_type,
        "created_at": survey.created_at,
    }


# ============================================================================
# Feature Requests
# ============================================================================

class FeatureRequestCreate(BaseModel):
    title: str
    description: str


class FeatureRequestResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    votes: int
    status: str
    created_at: str


@router.post("/features")
async def create_feature_request(request: FeatureRequestCreate, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    req = cx_service.create_feature_request(user_id, request.title, request.description)
    return {"status": "OK", "request": _feature_to_dict(req)}


@router.get("/features")
async def list_feature_requests(status: str = None):
    reqs = cx_service.list_feature_requests(status)
    return {"status": "OK", "requests": [_feature_to_dict(r) for r in reqs]}


@router.post("/features/{request_id}/vote")
async def vote_feature_request(request_id: str):
    req = cx_service.vote_feature_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Feature request not found")
    return {"status": "OK", "request": _feature_to_dict(req)}


def _feature_to_dict(req) -> Dict[str, Any]:
    return {
        "id": req.id,
        "user_id": req.user_id,
        "title": req.title,
        "description": req.description,
        "votes": req.votes,
        "status": req.status,
        "created_at": req.created_at,
    }


# ============================================================================
# Bug Reports
# ============================================================================

class BugReportCreate(BaseModel):
    title: str
    description: str
    severity: str = "medium"
    steps_to_reproduce: Optional[str] = None


class BugReportResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    severity: str
    status: str
    steps_to_reproduce: Optional[str]
    created_at: str


@router.post("/bugs")
async def create_bug_report(request: BugReportCreate, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    bug = cx_service.create_bug_report(user_id, request.title, request.description, request.severity, request.steps_to_reproduce)
    return {"status": "OK", "bug": _bug_to_dict(bug)}


@router.get("/bugs")
async def list_bug_reports(status: str = None):
    bugs = cx_service.list_bug_reports(status)
    return {"status": "OK", "bugs": [_bug_to_dict(b) for b in bugs]}


@router.patch("/bugs/{bug_id}")
async def update_bug_status(bug_id: str, status: str):
    bug = cx_service.update_bug_status(bug_id, status)
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report not found")
    return {"status": "OK", "bug": _bug_to_dict(bug)}


def _bug_to_dict(bug) -> Dict[str, Any]:
    return {
        "id": bug.id,
        "user_id": bug.user_id,
        "title": bug.title,
        "description": bug.description,
        "severity": bug.severity,
        "status": bug.status,
        "steps_to_reproduce": bug.steps_to_reproduce,
        "created_at": bug.created_at,
    }


# ============================================================================
# Customer Health
# ============================================================================

@router.get("/health/{user_id}")
async def get_customer_health(user_id: str):
    health = cx_service.calculate_health_score(user_id)
    return {"status": "OK", "health": _health_to_dict(health)}


@router.get("/health")
async def get_my_health(authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    health = cx_service.calculate_health_score(user_id)
    return {"status": "OK", "health": _health_to_dict(health)}


def _health_to_dict(health) -> Dict[str, Any]:
    return {
        "id": health.id,
        "user_id": health.user_id,
        "score": health.score,
        "factors": health.factors,
        "last_calculated": health.last_calculated,
        "created_at": health.created_at,
    }


# ============================================================================
# Support Analytics
# ============================================================================

class AnalyticCreate(BaseModel):
    metric_name: str
    metric_value: float
    period: str


@router.post("/analytics")
async def record_analytic(request: AnalyticCreate):
    analytic = cx_service.record_analytic(request.metric_name, request.metric_value, request.period)
    return {"status": "OK", "analytic": _analytic_to_dict(analytic)}


@router.get("/analytics")
async def list_analytics(metric_name: str = None, period: str = None):
    analytics = cx_service.get_analytics(metric_name, period)
    return {"status": "OK", "analytics": [_analytic_to_dict(a) for a in analytics]}


def _analytic_to_dict(analytic) -> Dict[str, Any]:
    return {
        "id": analytic.id,
        "metric_name": analytic.metric_name,
        "metric_value": analytic.metric_value,
        "period": analytic.period,
        "created_at": analytic.created_at,
    }


# ============================================================================
# Status Page
# ============================================================================

class IncidentCreate(BaseModel):
    title: str
    description: str
    affected_services: List[str] = []


class IncidentResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    affected_services: List[str]
    started_at: str
    resolved_at: Optional[str]
    created_at: str


@router.post("/incidents")
async def create_incident(request: IncidentCreate):
    incident = cx_service.create_incident(request.title, request.description, request.affected_services)
    return {"status": "OK", "incident": _incident_to_dict(incident)}


@router.get("/incidents")
async def list_incidents(status: str = None):
    incidents = cx_service.list_incidents(status)
    return {"status": "OK", "incidents": [_incident_to_dict(i) for i in incidents]}


@router.get("/status")
async def get_status_summary():
    summary = cx_service.get_status_summary()
    return {"status": "OK", "summary": summary}


@router.patch("/incidents/{incident_id}")
async def update_incident(incident_id: str, status: str):
    incident = cx_service.update_incident_status(incident_id, status)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "OK", "incident": _incident_to_dict(incident)}


def _incident_to_dict(incident) -> Dict[str, Any]:
    return {
        "id": incident.id,
        "title": incident.title,
        "description": incident.description,
        "status": incident.status,
        "affected_services": incident.affected_services,
        "started_at": incident.started_at,
        "resolved_at": incident.resolved_at,
        "created_at": incident.created_at,
    }


# ============================================================================
# Onboarding
# ============================================================================

class OnboardingStep(BaseModel):
    step: str


@router.post("/onboarding/start")
async def start_onboarding(authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    progress = cx_service.start_onboarding(user_id)
    return {"status": "OK", "progress": _onboarding_to_dict(progress)}


@router.post("/onboarding/step")
async def complete_onboarding_step(request: OnboardingStep, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    progress = cx_service.complete_onboarding_step(user_id, request.step)
    if not progress:
        raise HTTPException(status_code=404, detail="Onboarding not started")
    return {"status": "OK", "progress": _onboarding_to_dict(progress)}


@router.post("/onboarding/complete")
async def complete_onboarding(authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    progress = cx_service.complete_onboarding(user_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Onboarding not started")
    return {"status": "OK", "progress": _onboarding_to_dict(progress)}


@router.get("/onboarding")
async def get_onboarding(authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    progress = cx_service.get_onboarding_progress(user_id)
    if not progress:
        return {"status": "OK", "progress": None}
    return {"status": "OK", "progress": _onboarding_to_dict(progress)}


def _onboarding_to_dict(progress) -> Dict[str, Any]:
    return {
        "id": progress.id,
        "user_id": progress.user_id,
        "current_step": progress.current_step,
        "completed_steps": progress.completed_steps,
        "completed": progress.completed,
        "started_at": progress.started_at,
        "completed_at": progress.completed_at,
    }


# ============================================================================
# Live Chat
# ============================================================================

class ChatSessionCreate(BaseModel):
    agent_id: Optional[str] = None


class ChatMessageCreate(BaseModel):
    message: str


@router.post("/chat/sessions")
async def create_chat_session(request: ChatSessionCreate, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    session = cx_service.create_chat_session(user_id, request.agent_id)
    return {"status": "OK", "session": _session_to_dict(session)}


@router.post("/chat/sessions/{session_id}/messages")
async def send_message(session_id: str, request: ChatMessageCreate, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    session = cx_service.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    msg = cx_service.send_chat_message(session_id, user_id, "user", request.message)
    return {"status": "OK", "message": _message_to_dict(msg)}


@router.get("/chat/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    session = cx_service.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    messages = cx_service.get_chat_messages(session_id)
    return {"status": "OK", "messages": [_message_to_dict(m) for m in messages]}


@router.post("/chat/sessions/{session_id}/end")
async def end_chat_session(session_id: str):
    session = cx_service.end_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "OK", "session": _session_to_dict(session)}


@router.get("/chat/sessions")
async def list_sessions(authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    sessions = cx_service.list_user_sessions(user_id)
    return {"status": "OK", "sessions": [_session_to_dict(s) for s in sessions]}


def _session_to_dict(session) -> Dict[str, Any]:
    return {
        "id": session.id,
        "user_id": session.user_id,
        "agent_id": session.agent_id,
        "status": session.status,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
    }


def _message_to_dict(msg) -> Dict[str, Any]:
    return {
        "id": msg.id,
        "session_id": msg.session_id,
        "sender_id": msg.sender_id,
        "sender_type": msg.sender_type,
        "message": msg.message,
        "created_at": msg.created_at,
    }


# ============================================================================
# Support Tickets (expanded)
# ============================================================================

class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "medium"
    category: str = "general"


class TicketResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    subject: str
    description: str
    priority: str
    status: str
    category: str
    assigned_to: Optional[str]
    tags: List[str]
    created_at: str
    updated_at: str
    resolved_at: Optional[str]


@router.post("/tickets")
async def create_ticket(request: TicketCreate, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    from app.support import support_ticket_service
    ticket = support_ticket_service.create_ticket("default", user_id, request.subject, request.description, request.priority, request.category)
    return {"status": "OK", "ticket": _ticket_to_dict(ticket)}


@router.get("/tickets")
async def list_tickets(status: str = None, authorization: str = Header(None)):
    from app.support import support_ticket_service
    user_id = _get_user_id(authorization)
    tickets = support_ticket_service.list_tickets(tenant_id="default", status=status)
    return {"status": "OK", "tickets": [_ticket_to_dict(t) for t in tickets]}


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    from app.support import support_ticket_service
    ticket = support_ticket_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "OK", "ticket": _ticket_to_dict(ticket)}


@router.patch("/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, status: str = None, assigned_to: str = None):
    from app.support import support_ticket_service
    ticket = support_ticket_service.update_ticket(ticket_id, status=status, assigned_to=assigned_to)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "OK", "ticket": _ticket_to_dict(ticket)}


def _ticket_to_dict(ticket) -> Dict[str, Any]:
    return {
        "id": ticket.id,
        "tenant_id": ticket.tenant_id,
        "user_id": ticket.user_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "priority": ticket.priority,
        "status": ticket.status,
        "category": ticket.category,
        "assigned_to": ticket.assigned_to,
        "tags": ticket.tags,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at,
    }


# ============================================================================
# Customer Portal
# ============================================================================

@router.get("/portal")
async def get_portal(authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    health = cx_service.calculate_health_score(user_id)
    tickets = []
    from app.support import support_ticket_service
    for t in support_ticket_service.list_tickets(tenant_id="default"):
        if t.user_id == user_id:
            tickets.append(_ticket_to_dict(t))
    progress = cx_service.get_onboarding_progress(user_id)
    return {
        "status": "OK",
        "portal": {
            "health": _health_to_dict(health),
            "tickets": tickets,
            "onboarding": _onboarding_to_dict(progress) if progress else None,
        }
    }


def _get_user_id(authorization: str = None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        from app.utils.auth.auth_utils import get_user_id_from_token
        return get_user_id_from_token(authorization)
    except Exception:
        return "anonymous"
