import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.omnipresent_system import (
    OmnipresentEngine,
    AmbientContext,
    DevicePresence,
    DeviceType,
    EnvironmentType,
    HandoffSession,
    SocialPresence,
    SocialPresenceStatus,
    CollectiveMindState,
    AmbientSensing,
    ProactiveAction,
    EnvironmentalControl,
    PresenceMode,
    TimeContext,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["omnipresent"])

_engine = OmnipresentEngine()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# Request / Response Models
# ============================================================================

class RegisterDeviceRequest(BaseModel):
    device_type: str = "web"
    capabilities: List[str] = Field(default_factory=list)


class HandoffRequest(BaseModel):
    source_device_id: str
    target_device_id: str


class SocialPresenceUpdateRequest(BaseModel):
    status: str = "alone"
    nearby_users: List[str] = Field(default_factory=list)


class CollectiveMindCreateRequest(BaseModel):
    group_id: str
    participants: List[str] = Field(default_factory=list)


class SensingRecordRequest(BaseModel):
    sensor_type: str = "proximity"
    value: float = 0.0
    unit: str = ""
    confidence: float = 1.0


class EnvironmentalControlRequest(BaseModel):
    control_type: str = "lighting"
    value: Any = None
    unit: str = ""


class ContextResponse(BaseModel):
    context_id: str
    user_id: str
    timestamp: float
    location: Optional[Dict[str, Any]] = None
    environment: str
    time_context: str
    social_presence: str
    device_type: str
    presence_mode: str
    ambient_light_level: float
    noise_level: float
    connectivity: str
    battery_level: Optional[float] = None
    activity_type: str
    attention_focus: str
    proximity_devices: List[str]
    metadata: Dict[str, Any]


class DeviceResponse(BaseModel):
    device_id: str
    device_type: str
    user_id: str
    is_active: bool
    last_seen: float
    capabilities: List[str]
    handoff_status: str
    sync_state: Dict[str, Any]


class HandoffResponse(BaseModel):
    session_id: str
    source_device_id: str
    target_device_id: str
    user_id: str
    status: str
    initiated_at: float
    completed_at: Optional[float] = None
    error: Optional[str] = None


class SocialPresenceResponse(BaseModel):
    presence_id: str
    user_id: str
    status: str
    nearby_users: List[str]
    group_id: Optional[str] = None
    last_activity: float
    attention_direction: Optional[str] = None
    shared_context: Dict[str, Any]


class CollectiveMindResponse(BaseModel):
    mind_id: str
    group_id: str
    participants: List[str]
    shared_thoughts: List[Dict[str, Any]]
    collective_intent: str
    consensus_level: float
    emergent_insights: List[str]
    telepathic_bandwidth: float
    timestamp: float


class AmbientSensingResponse(BaseModel):
    sensing_id: str
    device_id: str
    sensor_type: str
    value: float
    unit: str
    confidence: float
    timestamp: float
    processed: bool
    response_triggered: bool


class ProactiveActionResponse(BaseModel):
    action_id: str
    user_id: str
    action_type: str
    predicted_need: str
    confidence: float
    status: str
    timestamp: float


class EnvironmentalControlResponse(BaseModel):
    control_id: str
    device_id: str
    control_type: str
    value: Any
    unit: str
    applied: bool
    timestamp: float


# ============================================================================
# Omnipresent Presence Endpoints
# ============================================================================

@router.get("/omnipresent/context")
async def get_ambient_context(authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    context = _engine.get_latest_context(user_id)
    if not context:
        from app.omnipresent_system import _simulate_context
        context = _simulate_context(user_id)
    return {
        "status": "OK",
        "context": {
            "context_id": context.context_id,
            "user_id": context.user_id,
            "timestamp": context.timestamp,
            "location": context.location,
            "environment": context.environment.value,
            "time_context": context.time_context.value,
            "social_presence": context.social_presence.value,
            "device_type": context.device_type.value,
            "presence_mode": context.presence_mode.value,
            "ambient_light_level": context.ambient_light_level,
            "noise_level": context.noise_level,
            "connectivity": context.connectivity,
            "battery_level": context.battery_level,
            "activity_type": context.activity_type,
            "attention_focus": context.attention_focus,
            "proximity_devices": context.proximity_devices,
            "metadata": context.metadata,
        },
    }


@router.get("/omnipresent/context/history")
async def get_context_history(limit: int = 50, authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    history = _engine.get_context_history(user_id, limit=limit)
    return {
        "status": "OK",
        "history": [
            {
                "context_id": c.context_id,
                "timestamp": c.timestamp,
                "environment": c.environment.value,
                "time_context": c.time_context.value,
                "social_presence": c.social_presence.value,
                "device_type": c.device_type.value,
                "activity_type": c.activity_type,
                "attention_focus": c.attention_focus,
                "ambient_light_level": c.ambient_light_level,
                "noise_level": c.noise_level,
                "connectivity": c.connectivity,
            }
            for c in history
        ],
    }


# ============================================================================
# Device Presence & Multi-Device Handoff
# ============================================================================

@router.post("/omnipresent/devices/register")
async def register_device(request: RegisterDeviceRequest, authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    try:
        device_type = DeviceType(request.device_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown device type: {request.device_type}")
    device = _engine.register_device(user_id, device_type, request.capabilities)
    return {
        "status": "OK",
        "device": {
            "device_id": device.device_id,
            "device_type": device.device_type.value,
            "user_id": device.user_id,
            "is_active": device.is_active,
            "last_seen": device.last_seen,
            "capabilities": device.capabilities,
            "handoff_status": device.handoff_status.value,
            "sync_state": device.sync_state,
        },
    }


@router.get("/omnipresent/devices")
async def list_devices(authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    devices = _engine.get_user_devices(user_id)
    return {
        "status": "OK",
        "devices": [
            {
                "device_id": d.device_id,
                "device_type": d.device_type.value,
                "is_active": d.is_active,
                "last_seen": d.last_seen,
                "capabilities": d.capabilities,
                "handoff_status": d.handoff_status.value,
                "sync_state": d.sync_state,
            }
            for d in devices
        ],
    }


@router.post("/omnipresent/handoff")
async def initiate_handoff(request: HandoffRequest, authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    context = _engine.get_latest_context(user_id)
    session = _engine.initiate_handoff(user_id, request.source_device_id, request.target_device_id, context)
    return {
        "status": "OK",
        "handoff": {
            "session_id": session.session_id,
            "source_device_id": session.source_device_id,
            "target_device_id": session.target_device_id,
            "user_id": session.user_id,
            "status": session.status.value,
            "initiated_at": session.initiated_at,
            "completed_at": session.completed_at,
            "error": session.error,
        },
    }


@router.get("/omnipresent/handoff/history")
async def get_handoff_history(authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    history = _engine.get_handoff_history(user_id)
    return {
        "status": "OK",
        "history": [
            {
                "session_id": h.session_id,
                "source_device_id": h.source_device_id,
                "target_device_id": h.target_device_id,
                "status": h.status.value,
                "initiated_at": h.initiated_at,
                "completed_at": h.completed_at,
                "error": h.error,
            }
            for h in history
        ],
    }


# ============================================================================
# Social Presence & Collaborative Telepathy
# ============================================================================

@router.post("/omnipresent/social/presence")
async def update_social_presence(request: SocialPresenceUpdateRequest, authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    try:
        status = SocialPresenceStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown social presence status: {request.status}")
    presence = _engine.update_social_presence(user_id, status, request.nearby_users)
    return {
        "status": "OK",
        "presence": {
            "presence_id": presence.presence_id,
            "user_id": presence.user_id,
            "status": presence.status.value,
            "nearby_users": presence.nearby_users,
            "group_id": presence.group_id,
            "last_activity": presence.last_activity,
            "attention_direction": presence.attention_direction,
            "shared_context": presence.shared_context,
        },
    }


@router.get("/omnipresent/social/presence")
async def get_social_presence(authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    presence = _engine.get_social_presence(user_id)
    if not presence:
        presence = _engine.update_social_presence(user_id, SocialPresenceStatus.ALONE)
    return {
        "status": "OK",
        "presence": {
            "presence_id": presence.presence_id,
            "user_id": presence.user_id,
            "status": presence.status.value,
            "nearby_users": presence.nearby_users,
            "group_id": presence.group_id,
            "last_activity": presence.last_activity,
            "attention_direction": presence.attention_direction,
            "shared_context": presence.shared_context,
        },
    }


@router.post("/omnipresent/collective/mind")
async def create_collective_mind(request: CollectiveMindCreateRequest):
    mind = _engine.create_collective_mind(request.group_id, request.participants)
    return {
        "status": "OK",
        "mind": {
            "mind_id": mind.mind_id,
            "group_id": mind.group_id,
            "participants": mind.participants,
            "shared_thoughts": mind.shared_thoughts,
            "collective_intent": mind.collective_intent,
            "consensus_level": mind.consensus_level,
            "emergent_insights": mind.emergent_insights,
            "telepathic_bandwidth": mind.telepathic_bandwidth,
            "timestamp": mind.timestamp,
        },
    }


@router.get("/omnipresent/collective/mind/{group_id}")
async def get_collective_mind(group_id: str):
    mind = _engine.get_collective_mind(group_id)
    if not mind:
        raise HTTPException(status_code=404, detail="Collective mind not found")
    return {
        "status": "OK",
        "mind": {
            "mind_id": mind.mind_id,
            "group_id": mind.group_id,
            "participants": mind.participants,
            "shared_thoughts": mind.shared_thoughts,
            "collective_intent": mind.collective_intent,
            "consensus_level": mind.consensus_level,
            "emergent_insights": mind.emergent_insights,
            "telepathic_bandwidth": mind.telepathic_bandwidth,
            "timestamp": mind.timestamp,
        },
    }


# ============================================================================
# Ambient Sensing & Response
# ============================================================================

@router.post("/omnipresent/sensing")
async def record_sensing(device_id: str, request: SensingRecordRequest):
    sensing = _engine.record_sensing(device_id, request.sensor_type, request.value, request.unit, request.confidence)
    return {
        "status": "OK",
        "sensing": {
            "sensing_id": sensing.sensing_id,
            "device_id": sensing.device_id,
            "sensor_type": sensing.sensor_type,
            "value": sensing.value,
            "unit": sensing.unit,
            "confidence": sensing.confidence,
            "timestamp": sensing.timestamp,
            "processed": sensing.processed,
            "response_triggered": sensing.response_triggered,
        },
    }


@router.get("/omnipresent/sensing/{device_id}")
async def get_sensings(device_id: str, count: int = 50):
    sensings = _engine.get_recent_sensings(device_id, count=count)
    return {
        "status": "OK",
        "sensings": [
            {
                "sensing_id": s.sensing_id,
                "sensor_type": s.sensor_type,
                "value": s.value,
                "unit": s.unit,
                "confidence": s.confidence,
                "timestamp": s.timestamp,
                "processed": s.processed,
                "response_triggered": s.response_triggered,
            }
            for s in sensings
        ],
    }


# ============================================================================
# Proactive Assistance
# ============================================================================

@router.get("/omnipresent/assistance/predict")
async def predict_proactive_action(authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    context = _engine.get_latest_context(user_id)
    if not context:
        from app.omnipresent_system import _simulate_context
        context = _simulate_context(user_id)
    action = _engine.predict_proactive_action(user_id, context)
    return {
        "status": "OK",
        "action": {
            "action_id": action.action_id,
            "user_id": action.user_id,
            "action_type": action.action_type,
            "predicted_need": action.predicted_need,
            "confidence": action.confidence,
            "status": action.status,
            "timestamp": action.timestamp,
        },
    }


@router.get("/omnipresent/assistance/history")
async def get_proactive_actions(authorization: Optional[str] = None):
    user_id = authorization or "anonymous"
    actions = _engine.get_proactive_actions(user_id)
    return {
        "status": "OK",
        "actions": [
            {
                "action_id": a.action_id,
                "action_type": a.action_type,
                "predicted_need": a.predicted_need,
                "confidence": a.confidence,
                "status": a.status,
                "timestamp": a.timestamp,
            }
            for a in actions
        ],
    }


# ============================================================================
# Environmental Controls
# ============================================================================

@router.post("/omnipresent/environment/control")
async def apply_environmental_control(device_id: str, request: EnvironmentalControlRequest):
    control = _engine.apply_environmental_control(device_id, request.control_type, request.value, request.unit)
    return {
        "status": "OK",
        "control": {
            "control_id": control.control_id,
            "device_id": control.device_id,
            "control_type": control.control_type,
            "value": control.value,
            "unit": control.unit,
            "applied": control.applied,
            "timestamp": control.timestamp,
        },
    }


@router.get("/omnipresent/environment/controls/{device_id}")
async def get_environmental_controls(device_id: str):
    controls = _engine.get_environmental_controls(device_id)
    return {
        "status": "OK",
        "controls": [
            {
                "control_id": c.control_id,
                "control_type": c.control_type,
                "value": c.value,
                "unit": c.unit,
                "applied": c.applied,
                "timestamp": c.timestamp,
            }
            for c in controls
        ],
    }


# ============================================================================
# Contextual Awareness & Time-Aware
# ============================================================================

@router.get("/omnipresent/time/context")
async def get_time_context():
    from app.omnipresent_system import _get_time_context
    ctx = _get_time_context()
    return {
        "status": "OK",
        "time_context": ctx.value,
        "suggested_ui_mode": "focus" if ctx in [TimeContext.MORNING, TimeContext.EARLY_MORNING] else "ambient",
    }
