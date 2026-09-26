"""Omnipresent system for ubiquitous AI presence across devices, environments, and contexts."""

import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional


class PresenceMode(str, Enum):
    AMBIENT = "ambient"
    ACTIVE = "active"
    PASSIVE = "passive"
    COLLECTIVE = "collective"
    TELEPATHIC = "telepathic"


class DeviceType(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    EXTENSION = "extension"
    EDITOR = "editor"
    WEARABLE = "wearable"
    IoT = "iot"
    VEHICLE = "vehicle"
    HOME = "home"
    WORK = "work"


class EnvironmentType(str, Enum):
    HOME = "home"
    WORK = "work"
    PUBLIC = "public"
    TRANSIT = "transit"
    NATURE = "nature"
    SOCIAL = "social"
    QUIET = "quiet"
    NOISY = "noisy"
    PRIVATE = "private"
    CROWDED = "crowded"


class TimeContext(str, Enum):
    EARLY_MORNING = "early_morning"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    LATE_NIGHT = "late_night"


class SocialPresenceStatus(str, Enum):
    ALONE = "alone"
    SMALL_GROUP = "small_group"
    LARGE_GROUP = "large_group"
    ONE_ON_ONE = "one_on_one"
    PUBLIC = "public"
    FOCUSED = "focused"


class HandoffStatus(str, Enum):
    IDLE = "idle"
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AmbientContext:
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    timestamp: float = field(default_factory=time.time)
    location: Optional[Dict[str, Any]] = None
    environment: EnvironmentType = EnvironmentType.HOME
    time_context: TimeContext = TimeContext.MORNING
    social_presence: SocialPresenceStatus = SocialPresenceStatus.ALONE
    device_type: DeviceType = DeviceType.WEB
    presence_mode: PresenceMode = PresenceMode.AMBIENT
    ambient_light_level: float = 0.5
    noise_level: float = 0.3
    connectivity: str = "online"
    battery_level: Optional[float] = None
    activity_type: str = "idle"
    attention_focus: str = "general"
    proximity_devices: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DevicePresence:
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_type: DeviceType = DeviceType.WEB
    user_id: str = ""
    is_active: bool = False
    last_seen: float = field(default_factory=time.time)
    capabilities: List[str] = field(default_factory=list)
    current_context: Optional[AmbientContext] = None
    handoff_status: HandoffStatus = HandoffStatus.IDLE
    sync_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_device_id: str = ""
    target_device_id: str = ""
    user_id: str = ""
    status: HandoffStatus = HandoffStatus.INITIATED
    context_snapshot: Optional[AmbientContext] = None
    transferred_state: Dict[str, Any] = field(default_factory=dict)
    initiated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error: Optional[str] = None


@dataclass
class SocialPresence:
    presence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    status: SocialPresenceStatus = SocialPresenceStatus.ALONE
    nearby_users: List[str] = field(default_factory=list)
    group_id: Optional[str] = None
    last_activity: float = field(default_factory=time.time)
    attention_direction: Optional[str] = None
    shared_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectiveMindState:
    mind_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    group_id: str = ""
    participants: List[str] = field(default_factory=list)
    shared_thoughts: List[Dict[str, Any]] = field(default_factory=list)
    collective_intent: str = ""
    consensus_level: float = 0.0
    emergent_insights: List[str] = field(default_factory=list)
    telepathic_bandwidth: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AmbientSensing:
    sensing_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = ""
    sensor_type: str = "proximity"
    value: float = 0.0
    unit: str = ""
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    processed: bool = False
    response_triggered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProactiveAction:
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    action_type: str = ""
    trigger_context: Optional[AmbientContext] = None
    predicted_need: str = ""
    confidence: float = 0.0
    status: str = "pending"
    executed_at: Optional[float] = None
    result: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class EnvironmentalControl:
    control_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = ""
    control_type: str = "lighting"
    value: Any = None
    unit: str = ""
    applied: bool = False
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


def _get_time_context(now: Optional[datetime] = None) -> TimeContext:
    now = now or datetime.now(timezone.utc)
    hour = now.hour
    if 5 <= hour < 7:
        return TimeContext.EARLY_MORNING
    if 7 <= hour < 12:
        return TimeContext.MORNING
    if 12 <= hour < 14:
        return TimeContext.MIDDAY
    if 14 <= hour < 17:
        return TimeContext.AFTERNOON
    if 17 <= hour < 21:
        return TimeContext.EVENING
    if 21 <= hour < 24:
        return TimeContext.NIGHT
    return TimeContext.LATE_NIGHT


def _simulate_context(user_id: str, device_type: DeviceType = DeviceType.WEB) -> AmbientContext:
    now = datetime.now(timezone.utc)
    env_types = list(EnvironmentType)
    social_types = list(SocialPresenceStatus)
    return AmbientContext(
        user_id=user_id,
        timestamp=now.timestamp(),
        location={"lat": random.uniform(-90, 90), "lon": random.uniform(-180, 180), "accuracy_m": random.uniform(5, 50)},
        environment=random.choice(env_types),
        time_context=_get_time_context(now),
        social_presence=random.choice(social_types),
        device_type=device_type,
        presence_mode=random.choice(list(PresenceMode)),
        ambient_light_level=random.uniform(0.0, 1.0),
        noise_level=random.uniform(0.0, 1.0),
        connectivity=random.choice(["online", "degraded", "offline"]),
        battery_level=random.uniform(0.1, 1.0),
        activity_type=random.choice(["idle", "working", "commuting", "relaxing", "socializing"]),
        attention_focus=random.choice(["general", "focused", "distracted", "deep_work"]),
        proximity_devices=[str(uuid.uuid4()) for _ in range(random.randint(0, 5))],
    )


class OmnipresentEngine:
    def __init__(self) -> None:
        self._contexts: Dict[str, List[AmbientContext]] = {}
        self._devices: Dict[str, DevicePresence] = {}
        self._handoffs: Dict[str, HandoffSession] = {}
        self._social_presences: Dict[str, SocialPresence] = {}
        self._collective_minds: Dict[str, CollectiveMindState] = {}
        self._sensors: Dict[str, List[AmbientSensing]] = {}
        self._actions: Dict[str, List[ProactiveAction]] = {}
        self._controls: Dict[str, List[EnvironmentalControl]] = {}
        self._listeners: List[Callable[[AmbientContext], Awaitable[None]]] = []
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

    def start(self, user_id: str) -> None:
        self._running = True
        self._task = asyncio.create_task(self._ambient_loop(user_id))

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    def add_listener(self, listener: Callable[[AmbientContext], Awaitable[None]]) -> None:
        self._listeners.append(listener)

    async def _ambient_loop(self, user_id: str) -> None:
        while self._running:
            context = _simulate_context(user_id)
            self._contexts.setdefault(user_id, []).append(context)
            if len(self._contexts[user_id]) > 200:
                self._contexts[user_id] = self._contexts[user_id][-200:]
            for listener in self._listeners:
                asyncio.create_task(self._safe_listener(listener, context))
            await asyncio.sleep(5.0)

    async def _safe_listener(self, listener: Callable[[AmbientContext], Awaitable[None]], context: AmbientContext) -> None:
        try:
            await listener(context)
        except Exception:
            pass

    def register_device(self, user_id: str, device_type: DeviceType, capabilities: Optional[List[str]] = None) -> DevicePresence:
        device = DevicePresence(
            user_id=user_id,
            device_type=device_type,
            capabilities=capabilities or [],
            is_active=True,
        )
        self._devices[device.device_id] = device
        return device

    def get_user_devices(self, user_id: str) -> List[DevicePresence]:
        return [d for d in self._devices.values() if d.user_id == user_id]

    def initiate_handoff(self, user_id: str, source_id: str, target_id: str, context_snapshot: Optional[AmbientContext] = None) -> HandoffSession:
        session = HandoffSession(
            source_device_id=source_id,
            target_device_id=target_id,
            user_id=user_id,
            status=HandoffStatus.IN_PROGRESS,
            context_snapshot=context_snapshot,
            transferred_state={"context": context_snapshot.__dict__ if context_snapshot else {}},
        )
        self._handoffs[session.session_id] = session
        session.completed_at = time.time()
        session.status = HandoffStatus.COMPLETED
        return session

    def get_handoff_history(self, user_id: str) -> List[HandoffSession]:
        return [h for h in self._handoffs.values() if h.user_id == user_id]

    def update_social_presence(self, user_id: str, status: SocialPresenceStatus, nearby_users: Optional[List[str]] = None) -> SocialPresence:
        presence = SocialPresence(
            user_id=user_id,
            status=status,
            nearby_users=nearby_users or [],
            last_activity=time.time(),
        )
        self._social_presences[user_id] = presence
        return presence

    def get_social_presence(self, user_id: str) -> Optional[SocialPresence]:
        return self._social_presences.get(user_id)

    def create_collective_mind(self, group_id: str, participants: List[str]) -> CollectiveMindState:
        mind = CollectiveMindState(
            group_id=group_id,
            participants=participants,
            collective_intent="",
            consensus_level=0.0,
        )
        self._collective_minds[mind.mind_id] = mind
        return mind

    def get_collective_mind(self, group_id: str) -> Optional[CollectiveMindState]:
        for mind in self._collective_minds.values():
            if mind.group_id == group_id:
                return mind
        return None

    def record_sensing(self, device_id: str, sensor_type: str, value: float, unit: str = "", confidence: float = 1.0) -> AmbientSensing:
        sensing = AmbientSensing(
            device_id=device_id,
            sensor_type=sensor_type,
            value=value,
            unit=unit,
            confidence=confidence,
        )
        self._sensors.setdefault(device_id, []).append(sensing)
        if len(self._sensors[device_id]) > 500:
            self._sensors[device_id] = self._sensors[device_id][-500:]
        return sensing

    def get_recent_sensings(self, device_id: str, count: int = 50) -> List[AmbientSensing]:
        items = self._sensors.get(device_id, [])
        return sorted(items, key=lambda s: s.timestamp, reverse=True)[:count]

    def predict_proactive_action(self, user_id: str, context: AmbientContext) -> ProactiveAction:
        action_types = ["lighting_adjust", "temperature_adjust", "notification_suppress", "app_launch", "focus_mode", "break_reminder", "context_switch"]
        predicted_type = random.choice(action_types)
        action = ProactiveAction(
            user_id=user_id,
            action_type=predicted_type,
            trigger_context=context,
            predicted_need=predicted_type.replace("_", " ").title(),
            confidence=random.uniform(0.6, 0.95),
        )
        self._actions.setdefault(user_id, []).append(action)
        if len(self._actions[user_id]) > 200:
            self._actions[user_id] = self._actions[user_id][-200:]
        return action

    def get_proactive_actions(self, user_id: str) -> List[ProactiveAction]:
        return sorted(self._actions.get(user_id, []), key=lambda a: a.timestamp, reverse=True)

    def apply_environmental_control(self, device_id: str, control_type: str, value: Any, unit: str = "") -> EnvironmentalControl:
        control = EnvironmentalControl(
            device_id=device_id,
            control_type=control_type,
            value=value,
            unit=unit,
            applied=True,
        )
        self._controls.setdefault(device_id, []).append(control)
        if len(self._controls[device_id]) > 200:
            self._controls[device_id] = self._controls[device_id][-200:]
        return control

    def get_environmental_controls(self, device_id: str) -> List[EnvironmentalControl]:
        return sorted(self._controls.get(device_id, []), key=lambda c: c.timestamp, reverse=True)

    def get_context_history(self, user_id: str, limit: int = 50) -> List[AmbientContext]:
        items = self._contexts.get(user_id, [])
        return sorted(items, key=lambda c: c.timestamp, reverse=True)[:limit]

    def get_latest_context(self, user_id: str) -> Optional[AmbientContext]:
        items = self._contexts.get(user_id, [])
        if not items:
            return None
        return sorted(items, key=lambda c: c.timestamp, reverse=True)[0]
