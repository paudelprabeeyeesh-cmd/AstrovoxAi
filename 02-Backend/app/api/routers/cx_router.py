"""Customer experience features: live chat, feedback, bug reports, feature requests, NPS, onboarding, tutorials, health, analytics, status page."""

from __future__ import annotations

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, status, Header, Query
from pydantic import BaseModel, Field

from app.utils.auth.auth_utils import get_user_id_from_token
from app.support import help_center_service

try:
    from database.database import get_db
except ImportError:
    from app.support import support_ticket_service as _sts
    get_db = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cx", tags=["customer-experience"])


# ============================================================================
# Helpers
# ============================================================================

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row, fields: List[str]) -> Dict[str, Any]:
    return {f: row[f] for f in fields if f in row.keys()}


# ============================================================================
# Live Chat
# ============================================================================

class CreateChatSessionRequest(BaseModel):
    agent_id: Optional[str] = None


class SendChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


@router.post("/chat/sessions")
async def create_chat_session(request: CreateChatSessionRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    session_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO live_chat_sessions (id, user_id, agent_id, status, started_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, request.agent_id, "open", _now()),
        )
        conn.commit()
    return {
        "status": "OK",
        "session": {
            "id": session_id,
            "user_id": user_id,
            "agent_id": request.agent_id,
            "status": "open",
            "started_at": _now(),
        },
    }


@router.post("/chat/sessions/{session_id}/messages")
async def send_chat_message(session_id: str, request: SendChatMessageRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    with get_db() as conn:
        session = conn.execute("SELECT id, status FROM live_chat_sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        msg_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO chat_messages (id, session_id, sender_id, sender_type, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, session_id, user_id, "user", request.message, _now()),
        )
        conn.commit()
    return {
        "status": "OK",
        "message": {
            "id": msg_id,
            "session_id": session_id,
            "sender_id": user_id,
            "sender_type": "user",
            "message": request.message,
            "created_at": _now(),
        },
    }


@router.get("/chat/sessions/{session_id}/messages")
async def get_chat_messages(session_id: str):
    with get_db() as conn:
        session = conn.execute("SELECT id FROM live_chat_sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        rows = conn.execute(
            "SELECT id, session_id, sender_id, sender_type, message, created_at FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
        messages = [
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "sender_id": r["sender_id"],
                "sender_type": r["sender_type"],
                "message": r["message"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    return {"status": "OK", "messages": messages}


@router.post("/chat/sessions/{session_id}/end")
async def end_chat_session(session_id: str):
    with get_db() as conn:
        conn.execute("UPDATE live_chat_sessions SET status = 'ended', ended_at = ? WHERE id = ?", (_now(), session_id))
        conn.commit()
    return {"status": "OK"}


@router.get("/chat/sessions")
async def list_chat_sessions(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, user_id, agent_id, status, started_at, ended_at FROM live_chat_sessions WHERE user_id = ? ORDER BY started_at DESC",
            (user_id,),
        ).fetchall()
        sessions = [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "agent_id": r["agent_id"],
                "status": r["status"],
                "started_at": r["started_at"],
                "ended_at": r["ended_at"],
            }
            for r in rows
        ]
    return {"status": "OK", "sessions": sessions}


# ============================================================================
# Feedback
# ============================================================================

class FeedbackRequest(BaseModel):
    type: str = Field(..., max_length=50)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)
    page_url: Optional[str] = Field(default=None, max_length=500)


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    fb_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO feedback (id, user_id, type, rating, comment, page_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fb_id, user_id, request.type, request.rating, request.comment, request.page_url, _now()),
        )
        conn.commit()
    return {
        "status": "OK",
        "feedback": {
            "id": fb_id,
            "user_id": user_id,
            "type": request.type,
            "rating": request.rating,
            "comment": request.comment,
            "page_url": request.page_url,
            "created_at": _now(),
        },
    }


@router.get("/feedback")
async def list_feedback(feedback_type: Optional[str] = Query(None)):
    with get_db() as conn:
        query = "SELECT id, user_id, type, rating, comment, page_url, created_at FROM feedback"
        params = []
        if feedback_type:
            query += " WHERE type = ?"
            params.append(feedback_type)
        query += " ORDER BY created_at DESC LIMIT 100"
        rows = conn.execute(query, params).fetchall()
        feedbacks = [_row_to_dict(r, ["id", "user_id", "type", "rating", "comment", "page_url", "created_at"]) for r in rows]
    return {"status": "OK", "feedback": feedbacks}


# ============================================================================
# Bug Reports
# ============================================================================

class BugReportRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    steps_to_reproduce: Optional[str] = Field(default=None, max_length=5000)


class BugReportUpdateRequest(BaseModel):
    status: str = Field(..., regex="^(open|in_progress|resolved|closed)$")


@router.post("/bugs")
async def create_bug_report(request: BugReportRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    bug_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO bug_reports (id, user_id, title, description, severity, status, steps_to_reproduce, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (bug_id, user_id, request.title, request.description, request.severity, "open", request.steps_to_reproduce, _now()),
        )
        conn.commit()
    return {
        "status": "OK",
        "bug": {
            "id": bug_id,
            "user_id": user_id,
            "title": request.title,
            "description": request.description,
            "severity": request.severity,
            "status": "open",
            "steps_to_reproduce": request.steps_to_reproduce,
            "created_at": _now(),
        },
    }


@router.get("/bugs")
async def list_bug_reports(status: Optional[str] = Query(None)):
    with get_db() as conn:
        query = "SELECT id, user_id, title, description, severity, status, steps_to_reproduce, created_at FROM bug_reports"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT 100"
        rows = conn.execute(query, params).fetchall()
        bugs = [_row_to_dict(r, ["id", "user_id", "title", "description", "severity", "status", "steps_to_reproduce", "created_at"]) for r in rows]
    return {"status": "OK", "bugs": bugs}


@router.patch("/bugs/{bug_id}")
async def update_bug_report(bug_id: str, request: BugReportUpdateRequest):
    with get_db() as conn:
        conn.execute("UPDATE bug_reports SET status = ? WHERE id = ?", (request.status, bug_id))
        conn.commit()
    return {"status": "OK"}


# ============================================================================
# Feature Requests
# ============================================================================

class FeatureRequestRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)


@router.post("/features")
async def create_feature_request(request: FeatureRequestRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    req_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO feature_requests (id, user_id, title, description, votes, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (req_id, user_id, request.title, request.description, 0, "open", _now()),
        )
        conn.commit()
    return {
        "status": "OK",
        "request": {
            "id": req_id,
            "user_id": user_id,
            "title": request.title,
            "description": request.description,
            "votes": 0,
            "status": "open",
            "created_at": _now(),
        },
    }


@router.get("/features")
async def list_feature_requests(status: Optional[str] = Query(None)):
    with get_db() as conn:
        query = "SELECT id, user_id, title, description, votes, status, created_at FROM feature_requests"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY votes DESC, created_at DESC LIMIT 100"
        rows = conn.execute(query, params).fetchall()
        requests = [_row_to_dict(r, ["id", "user_id", "title", "description", "votes", "status", "created_at"]) for r in rows]
    return {"status": "OK", "requests": requests}


@router.post("/features/{request_id}/vote")
async def vote_feature_request(request_id: str):
    with get_db() as conn:
        conn.execute("UPDATE feature_requests SET votes = votes + 1 WHERE id = ?", (request_id,))
        conn.commit()
    return {"status": "OK"}


# ============================================================================
# NPS Tracking
# ============================================================================

class NpsRequest(BaseModel):
    score: int = Field(..., ge=0, le=10)
    comment: Optional[str] = Field(default=None, max_length=2000)
    survey_type: str = Field(default="periodic", max_length=50)


@router.post("/nps")
async def submit_nps(request: NpsRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    survey_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO nps_surveys (id, user_id, score, comment, survey_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (survey_id, user_id, request.score, request.comment, request.survey_type, _now()),
        )
        conn.commit()
    return {
        "status": "OK",
        "survey": {
            "id": survey_id,
            "user_id": user_id,
            "score": request.score,
            "comment": request.comment,
            "survey_type": request.survey_type,
            "created_at": _now(),
        },
    }


@router.get("/nps/stats")
async def get_nps_stats():
    with get_db() as conn:
        rows = conn.execute("SELECT score FROM nps_surveys").fetchall()
        scores = [r["score"] for r in rows]
        total = len(scores)
        promoters = sum(1 for s in scores if s >= 9)
        detractors = sum(1 for s in scores if s <= 6)
        nps = ((promoters - detractors) / total * 100) if total > 0 else 0
    return {
        "status": "OK",
        "stats": {
            "total_responses": total,
            "promoters": promoters,
            "detractors": detractors,
            "nps_score": round(nps, 2),
            "average_score": round(sum(scores) / total, 2) if total > 0 else 0,
        },
    }


# ============================================================================
# Onboarding
# ============================================================================

class OnboardingStepRequest(BaseModel):
    step: str = Field(..., min_length=1, max_length=100)


@router.post("/onboarding/start")
async def start_onboarding(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    progress_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO onboarding_progress (id, user_id, current_step, completed_steps, completed, started_at) VALUES (?, ?, 0, '[]', 0, ?)",
            (progress_id, user_id, _now()),
        )
        conn.commit()
    return {
        "status": "OK",
        "progress": {
            "id": progress_id,
            "user_id": user_id,
            "current_step": 0,
            "completed_steps": [],
            "completed": False,
            "started_at": _now(),
        },
    }


@router.post("/onboarding/step")
async def complete_onboarding_step(request: OnboardingStepRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    with get_db() as conn:
        progress = conn.execute("SELECT * FROM onboarding_progress WHERE user_id = ?", (user_id,)).fetchone()
        if not progress:
            raise HTTPException(status_code=404, detail="Onboarding not started")
        completed_steps = json.loads(progress["completed_steps"] or "[]")
        if request.step not in completed_steps:
            completed_steps.append(request.step)
        conn.execute(
            "UPDATE onboarding_progress SET current_step = current_step + 1, completed_steps = ? WHERE user_id = ?",
            (json.dumps(completed_steps), user_id),
        )
        conn.commit()
    return {"status": "OK"}


@router.post("/onboarding/complete")
async def complete_onboarding(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    with get_db() as conn:
        conn.execute(
            "UPDATE onboarding_progress SET completed = 1, completed_at = ? WHERE user_id = ?",
            (_now(), user_id),
        )
        conn.commit()
    return {"status": "OK"}


@router.get("/onboarding")
async def get_onboarding(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    with get_db() as conn:
        progress = conn.execute("SELECT * FROM onboarding_progress WHERE user_id = ?", (user_id,)).fetchone()
        if not progress:
            return {"status": "OK", "progress": None}
        result = {
            "id": progress["id"],
            "user_id": progress["user_id"],
            "current_step": progress["current_step"],
            "completed_steps": json.loads(progress["completed_steps"] or "[]"),
            "completed": bool(progress["completed"]),
            "started_at": progress["started_at"],
            "completed_at": progress["completed_at"],
        }
    return {"status": "OK", "progress": result}


# ============================================================================
# Tutorials
# ============================================================================

@router.get("/tutorials")
async def list_tutorials(difficulty: Optional[str] = Query(None)):
    with get_db() as conn:
        query = "SELECT id, title, description, steps, difficulty, estimated_time, created_at, updated_at FROM tutorials"
        params = []
        if difficulty:
            query += " WHERE difficulty = ?"
            params.append(difficulty)
        rows = conn.execute(query, params).fetchall()
        tutorials = [
            {
                "id": r["id"],
                "title": r["title"],
                "description": r["description"],
                "steps": json.loads(r["steps"] or "[]"),
                "difficulty": r["difficulty"],
                "estimated_time": r["estimated_time"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
    return {"status": "OK", "tutorials": tutorials}


@router.get("/tutorials/{tutorial_id}")
async def get_tutorial(tutorial_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tutorials WHERE id = ?", (tutorial_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tutorial not found")
        tutorial = {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "steps": json.loads(row["steps"] or "[]"),
            "difficulty": row["difficulty"],
            "estimated_time": row["estimated_time"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    return {"status": "OK", "tutorial": tutorial}


@router.post("/tutorials/{tutorial_id}/start")
async def start_tutorial(tutorial_id: str, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    progress_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tutorial_progress (id, user_id, tutorial_id, current_step, completed, started_at) VALUES (?, ?, ?, 0, 0, ?)",
            (progress_id, user_id, tutorial_id, _now()),
        )
        conn.commit()
    return {
        "status": "OK",
        "progress": {
            "id": progress_id,
            "user_id": user_id,
            "tutorial_id": tutorial_id,
            "current_step": 0,
            "completed": False,
            "started_at": _now(),
        },
    }


@router.post("/tutorials/{tutorial_id}/progress")
async def update_tutorial_progress(tutorial_id: str, current_step: int = Query(..., ge=0), authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    with get_db() as conn:
        progress = conn.execute("SELECT * FROM tutorial_progress WHERE user_id = ? AND tutorial_id = ?", (user_id, tutorial_id)).fetchone()
        if not progress:
            raise HTTPException(status_code=404, detail="Tutorial progress not found")
        conn.execute(
            "UPDATE tutorial_progress SET current_step = ?, completed = ? WHERE id = ?",
            (current_step, 1 if current_step >= 10 else 0, progress["id"]),
        )
        conn.commit()
    return {"status": "OK"}


@router.get("/tutorials/progress")
async def get_tutorial_progress(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tutorial_progress WHERE user_id = ?", (user_id,)).fetchall()
        progress = [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "tutorial_id": r["tutorial_id"],
                "current_step": r["current_step"],
                "completed": bool(r["completed"]),
                "started_at": r["started_at"],
                "completed_at": r["completed_at"],
            }
            for r in rows
        ]
    return {"status": "OK", "progress": progress}


# ============================================================================
# Customer Health
# ============================================================================

@router.get("/health")
async def get_customer_health(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM customer_health WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            health_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO customer_health (id, user_id, score, factors, last_calculated, created_at) VALUES (?, ?, 0, '{}', ?, ?)",
                (health_id, user_id, _now(), _now()),
            )
            conn.commit()
            row = {
                "id": health_id,
                "user_id": user_id,
                "score": 0,
                "factors": "{}",
                "last_calculated": _now(),
                "created_at": _now(),
            }
        health = {
            "id": row["id"],
            "user_id": row["user_id"],
            "score": row["score"],
            "factors": json.loads(row["factors"] or "{}"),
            "last_calculated": row["last_calculated"],
            "created_at": row["created_at"],
        }
    return {"status": "OK", "health": health}


# ============================================================================
# Support Analytics
# ============================================================================

@router.post("/analytics")
async def record_analytic(metric_name: str = Query(...), metric_value: float = Query(...), period: str = Query(...)):
    analytic_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO support_analytics (id, metric_name, metric_value, period, created_at) VALUES (?, ?, ?, ?, ?)",
            (analytic_id, metric_name, metric_value, period, _now()),
        )
        conn.commit()
    return {"status": "OK", "analytic": {"id": analytic_id, "metric_name": metric_name, "metric_value": metric_value, "period": period, "created_at": _now()}}


@router.get("/analytics")
async def list_analytics(metric_name: Optional[str] = Query(None), period: Optional[str] = Query(None)):
    with get_db() as conn:
        query = "SELECT id, metric_name, metric_value, period, created_at FROM support_analytics WHERE 1=1"
        params = []
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)
        if period:
            query += " AND period = ?"
            params.append(period)
        query += " ORDER BY created_at DESC LIMIT 100"
        rows = conn.execute(query, params).fetchall()
        analytics = [_row_to_dict(r, ["id", "metric_name", "metric_value", "period", "created_at"]) for r in rows]
    return {"status": "OK", "analytics": analytics}


# ============================================================================
# Status Page
# ============================================================================

class IncidentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    affected_services: List[str] = Field(default_factory=list)


class IncidentUpdateRequest(BaseModel):
    status: str = Field(..., regex="^(investigating|identified|monitoring|resolved)$")


@router.post("/incidents")
async def create_incident(request: IncidentCreateRequest):
    incident_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO status_page_incidents (id, title, description, status, affected_services, started_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (incident_id, request.title, request.description, "investigating", json.dumps(request.affected_services), _now(), _now()),
        )
        conn.commit()
    return {
        "status": "OK",
        "incident": {
            "id": incident_id,
            "title": request.title,
            "description": request.description,
            "status": "investigating",
            "affected_services": request.affected_services,
            "started_at": _now(),
            "created_at": _now(),
        },
    }


@router.get("/incidents")
async def list_incidents(status: Optional[str] = Query(None)):
    with get_db() as conn:
        query = "SELECT id, title, description, status, affected_services, started_at, resolved_at, created_at FROM status_page_incidents"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT 50"
        rows = conn.execute(query, params).fetchall()
        incidents = [
            {
                "id": r["id"],
                "title": r["title"],
                "description": r["description"],
                "status": r["status"],
                "affected_services": json.loads(r["affected_services"] or "[]"),
                "started_at": r["started_at"],
                "resolved_at": r["resolved_at"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    return {"status": "OK", "incidents": incidents}


@router.get("/status")
async def get_status_summary():
    with get_db() as conn:
        rows = conn.execute("SELECT status, COUNT(*) as count FROM status_page_incidents GROUP BY status").fetchall()
        summary = {r["status"]: r["count"] for r in rows}
        active = conn.execute("SELECT COUNT(*) as c FROM status_page_incidents WHERE status != 'resolved'").fetchone()
    return {
        "status": "OK",
        "summary": {
            "overall": "operational" if (active["c"] if active else 0) == 0 else "degraded",
            "incidents_by_status": summary,
            "active_incidents": active["c"] if active else 0,
        },
    }


@router.patch("/incidents/{incident_id}")
async def update_incident(incident_id: str, request: IncidentUpdateRequest):
    with get_db() as conn:
        resolved_at = _now() if request.status == "resolved" else None
        conn.execute(
            "UPDATE status_page_incidents SET status = ?, resolved_at = ? WHERE id = ?",
            (request.status, resolved_at, incident_id),
        )
        conn.commit()
    return {"status": "OK"}


# ============================================================================
# Customer Portal
# ============================================================================

@router.get("/portal")
async def get_customer_portal(authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    with get_db() as conn:
        health_row = conn.execute("SELECT * FROM customer_health WHERE user_id = ?", (user_id,)).fetchone()
        health = {
            "score": health_row["score"] if health_row else 0,
            "factors": json.loads(health_row["factors"] or "{}") if health_row else {},
        }
        ticket_rows = conn.execute(
            "SELECT id, subject, status, priority, category, created_at FROM support_tickets WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
            (user_id,),
        ).fetchall()
        tickets = [
            {
                "id": r["id"],
                "subject": r["subject"],
                "status": r["status"],
                "priority": r["priority"],
                "category": r["category"],
                "created_at": r["created_at"],
            }
            for r in ticket_rows
        ]
        onboarding_row = conn.execute("SELECT * FROM onboarding_progress WHERE user_id = ?", (user_id,)).fetchone()
        onboarding = None
        if onboarding_row:
            onboarding = {
                "current_step": onboarding_row["current_step"],
                "completed": bool(onboarding_row["completed"]),
                "completed_steps": json.loads(onboarding_row["completed_steps"] or "[]"),
            }
    return {
        "status": "OK",
        "portal": {
            "health": health,
            "tickets": tickets,
            "onboarding": onboarding,
        },
    }
