
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import random

from ..neural import (
    NeuralSignal,
    NeuralSignalAPI,
    MotorImageryDecoder,
    EmotionDecoder,
    MemoryPalaceNavigator,
    DreamStateAssistant,
    LucidDreamingProtocol,
    ConsciousnessReadoutEngine,
    ThoughtToTextService,
    EmotionToUIService,
    AttentionAwareUIService,
    NeurofeedbackDashboardService,
    DecodingPipeline,
)

router = APIRouter(prefix="/neural", tags=["neural"])

_neural_api = NeuralSignalAPI()
_motor_decoder = MotorImageryDecoder()
_emotion_decoder = EmotionDecoder()
_memory_navigator = MemoryPalaceNavigator()
_dream_assistant = DreamStateAssistant()
_lucid_protocol = LucidDreamingProtocol(_dream_assistant)
_consciousness_engine = ConsciousnessReadoutEngine()
_thought_service = ThoughtToTextService()
_emotion_ui_service = EmotionToUIService()
_attention_ui_service = AttentionAwareUIService()
_neurofeedback_service = NeurofeedbackDashboardService()

try:
    _neural_api.create_pipeline(DecodingPipeline(pipeline_id="default-pipeline"))
except Exception:
    logger.warning("default neural pipeline creation failed", exc_info=True)


class PipelineCreateRequest(BaseModel):
    sample_rate_hz: float = 250.0
    epoch_duration_ms: int = 200
    features: List[str] = ["band_power", "hoc", "wsm", "asymmetry", "coherence"]


class PipelineCreateResponse(BaseModel):
    pipeline_id: str
    status: str


class NeuralEpochResponse(BaseModel):
    epoch_id: str
    channels: List[str]
    signal_quality: str
    timestamp: float


class MotorCommandResponse(BaseModel):
    command_id: str
    predicted_class: str
    confidence: float
    features: Dict[str, Any]
    timestamp: float


class EmotionResponse(BaseModel):
    reading_id: str
    dominant_emotion: str
    valence: float
    arousal: float
    emotion_scores: Dict[str, float]
    timestamp: float


class ThoughtToTextResponse(BaseModel):
    text: str
    tokens: List[str]
    confidence: float
    latency_ms: float
    epoch_id: str


class EmotionUIResponse(BaseModel):
    mood: str
    color_scheme: str
    animation_speed: str
    font_scale: float
    density: str
    confidence: float


class AttentionUIServiceResponse(BaseModel):
    engagement_score: float
    focus_level: str
    distraction_risk: float
    ui_adjustments: Dict[str, bool]


class NeurofeedbackResponse(BaseModel):
    epoch_id: str
    metrics: List[Dict[str, Any]]
    overall_score: float
    recommendations: List[str]


class DreamStateResponse(BaseModel):
    hypnogram_stage: str
    rem_sleep_ratio: float
    nrem_sleep_ratio: float
    dream_likelihood: float
    dream_clarity: float
    lucid_dream_readiness: float


class LucidProtocolResponse(BaseModel):
    active: bool
    attempts: int
    assisted_actions: List[str]


class ConsciousnessReadoutResponse(BaseModel):
    p300_detected: bool
    p300_latency_ms: Optional[float]
    erp_components: Dict[str, float]
    integrated_awareness: float
    metacognition: float
    working_memory_load: float


class MemoryPalaceNavigateResponse(BaseModel):
    palace_id: str
    node_id: str
    label: str
    position: List[float]
    connected_nodes: List[str]


@router.get("/status")
async def neural_status() -> Dict[str, Any]:
    return {
        "status": "operational",
        "device_id": _neural_api.device_id,
        "pipelines": list(_neural_api.pipelines.keys()),
        "modules": {
            "motor_imagery": True,
            "emotion_decoder": True,
            "memory_palace": True,
            "dream_assistant": True,
            "lucid_dreaming": True,
            "consciousness_readout": True,
            "thought_to_text": True,
            "emotion_ui_mapper": True,
            "attention_aware_ui": True,
            "neurofeedback_dashboard": True,
        },
    }


@router.post("/pipeline", response_model=PipelineCreateResponse)
async def create_pipeline(request: PipelineCreateRequest) -> PipelineCreateResponse:
    pipeline = DecodingPipeline(
        sample_rate_hz=request.sample_rate_hz,
        epoch_duration_ms=request.epoch_duration_ms,
        features=request.features,
    )
    pipeline_id = _neural_api.create_pipeline(pipeline)
    return PipelineCreateResponse(pipeline_id=pipeline_id, status="created")


@router.get("/epochs", response_model=List[NeuralEpochResponse])
async def get_epochs(count: int = 20) -> List[NeuralEpochResponse]:
    epochs = await _neural_api.get_recent_epochs(count=count)
    return [
        NeuralEpochResponse(
            epoch_id=e.epoch_id,
            channels=[c.value for c in e.channels],
            signal_quality=e.signal_quality.value,
            timestamp=e.timestamp,
        )
        for e in epochs
    ]


@router.post("/epoch/current")
async def get_current_epoch() -> Dict[str, Any]:
    epochs = await _neural_api.get_recent_epochs(count=1)
    if not epochs:
        return {"epoch_id": "", "channels": [], "signal_quality": "no_signal"}
    epoch = epochs[0]
    return {
        "epoch_id": epoch.epoch_id,
        "channels": [c.value for c in epoch.channels],
        "power_bands": [
            {"electrode": pb.electrode.value, "band": pb.band.value, "power": pb.power}
            for pb in epoch.power_bands
        ],
        "signal_quality": epoch.signal_quality.value,
        "timestamp": epoch.timestamp,
    }


@router.post("/motor-imagery", response_model=MotorCommandResponse)
async def predict_motor_imagery() -> MotorCommandResponse:
    epochs = await _neural_api.get_recent_epochs(count=1)
    if not epochs:
        return MotorCommandResponse(predicted_class="rest", confidence=0.0)
    epoch = epochs[0]
    command = _motor_decoder.predict(epoch)
    return MotorCommandResponse(
        command_id=command.command_id,
        predicted_class=command.predicted_class,
        confidence=command.confidence,
        features=command.features,
        timestamp=command.timestamp,
    )


@router.get("/motor-imagery/history")
async def motor_imagery_history() -> List[MotorCommandResponse]:
    return [
        MotorCommandResponse(
            command_id=c.command_id,
            predicted_class=c.predicted_class,
            confidence=c.confidence,
            features=c.features,
            timestamp=c.timestamp,
        )
        for c in _motor_decoder.history()[:50]
    ]


@router.post("/emotion", response_model=EmotionResponse)
async def predict_emotion() -> EmotionResponse:
    epochs = await _neural_api.get_recent_epochs(count=1)
    if not epochs:
        return EmotionResponse(dominant_emotion="neutral", valence=0.0, arousal=0.0)
    epoch = epochs[0]
    reading = _emotion_decoder.predict(epoch)
    return EmotionResponse(
        reading_id=reading.reading_id,
        dominant_emotion=reading.dominant_emotion,
        valence=reading.valence,
        arousal=reading.arousal,
        emotion_scores=reading.emotion_scores,
        timestamp=reading.timestamp,
    )


@router.get("/emotion/history")
async def emotion_history() -> List[EmotionResponse]:
    return [
        EmotionResponse(
            reading_id=r.reading_id,
            dominant_emotion=r.dominant_emotion,
            valence=r.valence,
            arousal=r.arousal,
            emotion_scores=r.emotion_scores,
            timestamp=r.timestamp,
        )
        for r in _emotion_decoder.recent()[:50]
    ]


@router.post("/thought-to-text", response_model=ThoughtToTextResponse)
async def thought_to_text() -> ThoughtToTextResponse:
    epochs = await _neural_api.get_recent_epochs(count=1)
    if not epochs:
        return ThoughtToTextResponse(text="", confidence=0.0)
    result = _thought_service.decode(epochs[0])
    return ThoughtToTextResponse(
        text=result["text"],
        tokens=result["tokens"],
        confidence=result["confidence"],
        latency_ms=result["latency_ms"],
        epoch_id=result["epoch_id"],
    )


@router.post("/emotion-ui", response_model=EmotionUIResponse)
async def emotion_to_ui() -> EmotionUIResponse:
    epochs = await _neural_api.get_recent_epochs(count=1)
    if not epochs:
        return EmotionUIResponse(mood="neutral")
    hint = _emotion_ui_service.map_emotion(epochs[0])
    return EmotionUIResponse(
        mood=hint["mood"],
        color_scheme=hint["color_scheme"],
        animation_speed=hint["animation_speed"],
        font_scale=hint["font_scale"],
        density=hint["density"],
        confidence=hint["confidence"],
    )


@router.post("/attention-ui", response_model=AttentionUIServiceResponse)
async def attention_aware_ui() -> AttentionUIServiceResponse:
    epochs = await _neural_api.get_recent_epochs(count=1)
    if not epochs:
        return AttentionUIServiceResponse(
            engagement_score=0.0, focus_level="low", distraction_risk=0.0
        )
    adaptation = _attention_ui_service.process_epoch(epochs[0])
    return AttentionUIServiceResponse(
        engagement_score=adaptation["engagement_score"],
        focus_level=adaptation["focus_level"],
        distraction_risk=adaptation["distraction_risk"],
        ui_adjustments=adaptation["ui_adjustments"],
    )


@router.get("/neurofeedback", response_model=NeurofeedbackResponse)
async def get_neurofeedback() -> NeurofeedbackResponse:
    epochs = await _neural_api.get_recent_epochs(count=1)
    if not epochs:
        return NeurofeedbackResponse(epoch_id="", metrics=[], overall_score=0.0)
    result = _neurofeedback_service.compute(epochs[0])
    return NeurofeedbackResponse(
        epoch_id=result["epoch_id"],
        metrics=result["metrics"],
        overall_score=result["overall_score"],
        recommendations=result["recommendations"],
    )


@router.post("/dream-state", response_model=DreamStateResponse)
async def dream_state() -> DreamStateResponse:
    epochs = await _neural_api.get_recent_epochs(count=1)
    reading = _dream_assistant.assist(epochs[0] if epochs else NeuralSignal())
    return DreamStateResponse(
        hypnogram_stage=reading.hypnogram_stage,
        rem_sleep_ratio=reading.rem_sleep_ratio,
        nrem_sleep_ratio=reading.nrem_sleep_ratio,
        dream_likelihood=reading.dream_likelihood,
        dream_clarity=reading.dream_clarity,
        lucid_dream_readiness=reading.lucid_dream_readiness,
    )


@router.post("/lucid-protocol/start")
async def start_lucid_protocol() -> Dict[str, Any]:
    _lucid_protocol.start_protocol()
    return {"status": "started"}


@router.post("/lucid-protocol/stop")
async def stop_lucid_protocol() -> Dict[str, Any]:
    _lucid_protocol.stop_protocol()
    return {"status": "stopped"}


@router.post("/lucid-protocol/tick", response_model=LucidProtocolResponse)
async def lucid_protocol_tick() -> LucidProtocolResponse:
    epochs = await _neural_api.get_recent_epochs(count=1)
    reading = _lucid_protocol.tick(epochs[0] if epochs else NeuralSignal())
    return LucidProtocolResponse(
        active=_lucid_protocol.active,
        attempts=_lucid_protocol.attempts,
        assisted_actions=reading.assisted_actions if reading else [],
    )


@router.get("/consciousness-readout", response_model=ConsciousnessReadoutResponse)
async def consciousness_readout() -> ConsciousnessReadoutResponse:
    epochs = await _neural_api.get_recent_epochs(count=1)
    readout = _consciousness_engine.generate(epochs[0] if epochs else NeuralSignal())
    return ConsciousnessReadoutResponse(
        p300_detected=readout.p300_detected,
        p300_latency_ms=readout.p300_latency_ms,
        erp_components=readout.erp_components,
        integrated_awareness=readout.integrated_awareness,
        metacognition=readout.metacognition,
        working_memory_load=readout.working_memory_load,
    )


@router.get("/memory-palace")
async def memory_palace() -> Dict[str, Any]:
    palace = _memory_navigator.current_palace() or []
    return {
        "palace_id": palace[0].palace_id if palace else "",
        "nodes": [
            {
                "node_id": n.node_id,
                "label": n.label,
                "position": n.position,
                "connected_nodes": n.connected_nodes,
                "tags": n.tags,
            }
            for n in palace
        ],
    }


@router.post("/memory-palace/navigate", response_model=MemoryPalaceNavigateResponse)
async def navigate_memory_palace(node_id: str) -> MemoryPalaceNavigateResponse:
    palace = _memory_navigator.current_palace() or []
    palace_id = palace[0].palace_id if palace else ""
    node = _memory_navigator.navigate(palace_id, node_id)
    if not node:
        return MemoryPalaceNavigateResponse(palace_id=palace_id, node_id=node_id)
    return MemoryPalaceNavigateResponse(
        palace_id=node.palace_id,
        node_id=node.node_id,
        label=node.label,
        position=list(node.position),
        connected_nodes=node.connected_nodes,
    )
