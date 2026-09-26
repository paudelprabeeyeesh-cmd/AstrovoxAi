"""Safety API routes."""

from fastapi import APIRouter

from app.safety.injection_defense import prompt_injection_defense
from app.safety.jailbreak import jailbreak_mitigator
from app.safety.pii_guard import pii_guard
from app.safety.moderation_pipeline import moderation_pipeline
from app.safety.red_team import red_team_runner, red_team_playbook
from app.safety.evaluation_harness import evaluation_harness
from app.safety.feedback import human_feedback_collector
from app.safety.risk_assessment import risk_assessor
from app.safety.scoring import safety_scorer
from app.safety.adversarial import adversarial_tester
from app.safety.audit import safety_audit_logger
from app.safety.monitoring import model_behavior_monitor
from app.safety.incident_response import incident_response

router = APIRouter(prefix="/safety", tags=["safety"])


@router.post("/check/injection")
async def check_injection(payload: dict):
    text = payload.get("text", "")
    result = prompt_injection_defense.full_pipeline("", text, "")
    return result


@router.post("/check/jailbreak")
async def check_jailbreak(payload: dict):
    text = payload.get("text", "")
    result = jailbreak_mitigator.mitigate(text)
    return result


@router.post("/check/pii")
async def check_pii(payload: dict):
    text = payload.get("text", "")
    redacted, matches = pii_guard.redact(text)
    return {"redacted": redacted, "matches": len(matches), "types": list({m.pii_type for m in matches})}


@router.post("/moderate")
async def moderate_output(payload: dict):
    text = payload.get("text", "")
    result = moderation_pipeline.moderate(text)
    return result


@router.get("/redteam/cases")
async def list_redteam_cases(category: str = None):
    cases = red_team_playbook.get_cases(category)
    return [{"id": c.id, "name": c.name, "category": c.category, "severity": c.severity} for c in cases]


@router.post("/redteam/run")
async def run_redteam(payload: dict):
    case_id = payload.get("case_id")
    case = red_team_playbook.get_case(case_id)
    if not case:
        return {"error": "Case not found"}
    model_func = lambda prompt: payload.get("mock_response", "I cannot comply with that request.")
    safety_func = lambda response: {"safe": True}
    result = red_team_runner.run_single(case, model_func)
    return {"case_id": result.case_id, "passed": result.passed, "severity": result.severity}


@router.get("/eval/datasets")
async def list_eval_datasets():
    return list(evaluation_harness._datasets.keys())


@router.get("/eval/summary")
async def eval_summary():
    return evaluation_harness.get_overall_score({})


@router.post("/feedback")
async def submit_feedback(payload: dict):
    entry = human_feedback_collector.submit_feedback(
        interaction_id=payload.get("interaction_id", ""),
        rating=payload.get("rating", 3),
        user_id=payload.get("user_id"),
        comment=payload.get("comment"),
        categories=payload.get("categories", []),
    )
    return {"id": entry.id, "status": "submitted"}


@router.get("/feedback/summary")
async def feedback_summary():
    return human_feedback_collector.get_feedback_summary()


@router.post("/risk/assess")
async def assess_risk(payload: dict):
    report = risk_assessor.assess(
        model_id=payload.get("model_id", "unknown"),
        feature=payload.get("feature", "general"),
    )
    return {
        "id": report.id,
        "model_id": report.model_id,
        "risk_level": report.risk_level.value,
        "score": report.score,
        "recommendations": report.recommendations,
    }


@router.post("/score")
async def compute_safety_score(payload: dict):
    metrics = payload.get("metrics", {})
    result = safety_scorer.calculate_overall_score(metrics)
    return result


@router.post("/adversarial/run")
async def run_adversarial(payload: dict):
    def model(prompt):
        return payload.get("mock_response", "I cannot comply with that request.")
    def safety(response):
        return {"safe": True}
    suite_result = adversarial_tester.run_suite(model, safety)
    return suite_result


@router.get("/audit/log")
async def get_audit_log(limit: int = 100, event_type: str = None, severity: str = None):
    entries = safety_audit_logger.get_entries(limit=limit, event_type=event_type, severity=severity)
    return [
        {
            "id": e.id,
            "timestamp": e.iso_timestamp,
            "event_type": e.event_type,
            "severity": e.severity,
            "action": e.action,
            "user_id": e.user_id,
        }
        for e in entries
    ]


@router.get("/audit/summary")
async def audit_summary():
    return safety_audit_logger.get_events_summary()


@router.get("/monitoring/health/{model_id}")
async def model_health(model_id: str):
    return model_behavior_monitor.get_model_health(model_id)


@router.get("/monitoring/alerts")
async def get_alerts(model_id: str = None, severity: str = None, limit: int = 100):
    alerts = model_behavior_monitor.get_alerts(model_id=model_id, severity=severity, limit=limit)
    return [
        {
            "id": a.id,
            "model_id": a.model_id,
            "metric": a.metric,
            "severity": a.severity,
            "value": a.value,
            "message": a.message,
            "timestamp": a.timestamp,
        }
        for a in alerts
    ]


@router.get("/incidents")
async def list_incidents(status: str = None):
    incidents = incident_response.get_open_incidents() if status == "open" else list(incident_response._incidents.values())
    return [
        {
            "id": i.id,
            "title": i.title,
            "severity": i.severity.value,
            "status": i.status.value,
            "model_id": i.model_id,
            "affected_users": i.affected_users,
            "created_at": i.created_at,
        }
        for i in incidents
    ]


@router.post("/incidents")
async def create_incident(payload: dict):
    from app.safety.incident_response import IncidentSeverity
    severity_str = payload.get("severity", "medium")
    try:
        severity = IncidentSeverity(severity_str)
    except ValueError:
        severity = IncidentSeverity.MEDIUM
    incident = incident_response.create_incident(
        title=payload.get("title", "Untitled Incident"),
        description=payload.get("description", ""),
        severity=severity,
        model_id=payload.get("model_id"),
        affected_users=payload.get("affected_users", 0),
    )
    return {"id": incident.id, "status": incident.status.value}
