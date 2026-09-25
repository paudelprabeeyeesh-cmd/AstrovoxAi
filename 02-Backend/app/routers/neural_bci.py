import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.futuristic_interfaces import (
    NeuralSignalAPI,
    MotorImageryDecoder,
    EmotionDecoder,
    MemoryPalaceNavigator,
    DreamStateAssistant,
    LucidDreamingProtocol,
    ConsciousnessReadoutEngine,
    DecodingPipeline,
    ElectrodeLocation,
    BandPower,
)
from app.auth import require_verified_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["neural-bci"])

_neural_api = NeuralSignalAPI()
_motor_decoder = MotorImageryDecoder()
_emotion_decoder = EmotionDecoder()
_memory_navigator = MemoryPalaceNavigator()
_dream_assistant = DreamStateAssistant()
_lucid_protocol = LucidDreamingProtocol(_dream_assistant)
_consciousness_engine = ConsciousnessReadoutEngine()


# ============================================================================
# Request / Response Models
# ============================================================================

class CreatePipelineRequest(BaseModel):
    sample_rate_hz: float = 250.0
    epoch_duration_ms: int = 200
    notch_filter_hz: Optional[float] = 60.0
    band_pass_hz: tuple = (1.0, 80.0)
    artifact_rejection: bool = True


class ThoughtToTextRequest(BaseModel):
    neural_embedding: list[float] = Field(default_factory=list)
    top_k: int = 1


class EmotionMappingRequest(BaseModel):
    valence: float = 0.0
    arousal: float = 0.0
    context: dict[str, Any] = Field(default_factory=dict)


class AttentionStateRequest(BaseModel):
    focus_score: float = 0.5
    distraction_signals: list[dict[str, Any]] = Field(default_factory=list)
    ui_context: dict[str, Any] = Field(default_factory=dict)


class MotorCommandRequest(BaseModel):
    epoch_data: list[list[float]] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)


class MemoryPalaceRegisterRequest(BaseModel):
    palace_id: str = ""
    nodes: list[dict[str, Any]] = Field(default_factory=list)


class MemoryPalaceNavigateRequest(BaseModel):
    palace_id: str = ""
    node_id: str = ""


class DreamAssistRequest(BaseModel):
    epoch_data: list[list[float]] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)


class LucidProtocolControlRequest(BaseModel):
    active: bool = False


class ConsciousnessReadoutRequest(BaseModel):
    epoch_data: list[list[float]] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    self_reported_clarity: Optional[float] = None


class BCIConnectRequest(BaseModel):
    device_id: str = "stub_device"
    device_type: str = "eeg"
    sample_rate_hz: float = 250.0


class SignalProcessRequest(BaseModel):
    signal: dict[str, Any] = Field(default_factory=dict)
    pipeline_id: str = ""


class EEGEMGMEGRequest(BaseModel):
    modality: str = "eeg"
    channels: list[str] = Field(default_factory=list)
    sample_rate_hz: float = 250.0


class DecoderModelRequest(BaseModel):
    model_type: str = "thought_to_text"
    input_data: dict[str, Any] = Field(default_factory=dict)


class BrainCommandRequest(BaseModel):
    command: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence_threshold: float = 0.7


# ============================================================================
# Neural Signal API
# ============================================================================

@router.post("/neural/pipelines")
async def create_pipeline(request: CreatePipelineRequest, user_id: str = Depends(require_verified_email)):
    try:
        pipeline = DecodingPipeline(
            sample_rate_hz=request.sample_rate_hz,
            epoch_duration_ms=request.epoch_duration_ms,
            notch_filter_hz=request.notch_filter_hz,
            band_pass_hz=tuple(request.band_pass_hz),
            artifact_rejection=request.artifact_rejection,
        )
        pipeline_id = _neural_api.create_pipeline(pipeline)
        return {
            "status": "OK",
            "pipeline_id": pipeline_id,
            "config": {
                "sample_rate_hz": pipeline.sample_rate_hz,
                "epoch_duration_ms": pipeline.epoch_duration_ms,
                "notch_filter_hz": pipeline.notch_filter_hz,
                "band_pass_hz": list(pipeline.band_pass_hz),
                "artifact_rejection": pipeline.artifact_rejection,
            },
        }
    except Exception as e:
        logger.error(f"Pipeline creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neural/pipelines/{pipeline_id}/start")
async def start_pipeline(pipeline_id: str, user_id: str = Depends(require_verified_email)):
    try:
        await _neural_api.start(pipeline_id)
        return {"status": "OK", "pipeline_id": pipeline_id, "running": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    except Exception as e:
        logger.error(f"Pipeline start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neural/pipelines/{pipeline_id}/stop")
async def stop_pipeline(pipeline_id: str, user_id: str = Depends(require_verified_email)):
    try:
        await _neural_api.stop()
        return {"status": "OK", "pipeline_id": pipeline_id, "running": False}
    except Exception as e:
        logger.error(f"Pipeline stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/epochs")
async def get_recent_epochs(count: int = 20, user_id: str = Depends(require_verified_email)):
    try:
        epochs = await _neural_api.get_recent_epochs(count)
        return {
            "status": "OK",
            "epochs": [
                {
                    "epoch_id": e.epoch_id,
                    "channels": [c.value for c in e.channels],
                    "sample_rate_hz": e.sample_rate_hz,
                    "signal_quality": e.signal_quality.value,
                    "artifacts_rejected": e.artifacts_rejected,
                    "timestamp": e.timestamp,
                    "power_bands": [
                        {
                            "electrode": pb.electrode.value,
                            "band": pb.band.value,
                            "power": pb.power,
                            "relative_power": pb.relative_power,
                        }
                        for pb in e.power_bands
                    ],
                }
                for e in epochs
            ],
        }
    except Exception as e:
        logger.error(f"Fetch epochs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Thought-to-Text
# ============================================================================

@router.post("/neural/thought-to-text")
async def thought_to_text(request: ThoughtToTextRequest, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.thought_to_text import ThoughtToTextService
        service = ThoughtToTextService()
        texts = service.generate(request.neural_embedding, top_k=request.top_k)
        return {"status": "OK", "texts": texts}
    except Exception as e:
        logger.error(f"Thought-to-text failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Emotion-to-UI Mapping
# ============================================================================

@router.post("/neural/emotion-to-ui")
async def emotion_to_ui(request: EmotionMappingRequest, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.emotion_mapping import EmotionToUIMappingService
        service = EmotionToUIMappingService()
        mapping = service.map_to_ui(request.valence, request.arousal, request.context)
        return {"status": "OK", "mapping": mapping}
    except Exception as e:
        logger.error(f"Emotion-to-UI mapping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/emotion")
async def get_current_emotion(user_id: str = Depends(require_verified_email)):
    try:
        recent = _emotion_decoder.recent()
        if recent:
            reading = recent[0]
            return {
                "status": "OK",
                "emotion": {
                    "dominant_emotion": reading.dominant_emotion,
                    "valence": reading.valence,
                    "arousal": reading.arousal,
                    "emotion_scores": reading.emotion_scores,
                    "signal_quality": reading.signal_quality.value,
                    "timestamp": reading.timestamp,
                },
            }
        return {"status": "OK", "emotion": None}
    except Exception as e:
        logger.error(f"Get emotion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Attention-aware UI Adaptation
# ============================================================================

@router.post("/neural/attention-adapt")
async def attention_adapt(request: AttentionStateRequest, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.attention_adapter import AttentionAwareAdapter
        adapter = AttentionAwareAdapter()
        adaptation = adapter.adapt_ui(request.focus_score, request.distraction_signals, request.ui_context)
        return {"status": "OK", "adaptation": adaptation}
    except Exception as e:
        logger.error(f"Attention adaptation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Motor Imagery Command System
# ============================================================================

@router.post("/neural/motor-imagery/command")
async def motor_imagery_command(request: MotorCommandRequest, user_id: str = Depends(require_verified_email)):
    try:
        epoch = _neural_api._simulate_epoch(
            [ElectrodeLocation[c] for c in request.channels] if request.channels else _neural_api._default_channels()
        )
        command = _motor_decoder.predict(epoch)
        return {
            "status": "OK",
            "command": {
                "command_id": command.command_id,
                "predicted_class": command.predicted_class,
                "confidence": command.confidence,
                "features": command.features,
                "timestamp": command.timestamp,
            },
        }
    except Exception as e:
        logger.error(f"Motor imagery command failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/motor-imagery/history")
async def motor_imagery_history(limit: int = 50, user_id: str = Depends(require_verified_email)):
    try:
        history = _motor_decoder.history()[:limit]
        return {
            "status": "OK",
            "history": [
                {
                    "command_id": c.command_id,
                    "predicted_class": c.predicted_class,
                    "confidence": c.confidence,
                    "features": c.features,
                    "timestamp": c.timestamp,
                }
                for c in history
            ],
        }
    except Exception as e:
        logger.error(f"Motor imagery history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Neurofeedback Dashboard
# ============================================================================

@router.get("/neural/neurofeedback/metrics")
async def neurofeedback_metrics(user_id: str = Depends(require_verified_email)):
    try:
        epochs = await _neural_api.get_recent_epochs(5)
        metrics = []
        if epochs:
            epoch = epochs[0]
            for pb in epoch.power_bands:
                metrics.append({
                    "metric": f"{pb.band.value}_power",
                    "electrode": pb.electrode.value,
                    "value": pb.power,
                    "relative_power": pb.relative_power,
                    "unit": "uV^2",
                    "quality": epoch.signal_quality.value,
                    "timestamp": epoch.timestamp,
                })
        return {"status": "OK", "metrics": metrics}
    except Exception as e:
        logger.error(f"Neurofeedback metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Memory Palace Navigation
# ============================================================================

@router.post("/neural/memory-palace/register")
async def memory_palace_register(request: MemoryPalaceRegisterRequest, user_id: str = Depends(require_verified_email)):
    try:
        nodes = [MemoryPalaceNode(**node) for node in request.nodes]
        palace_id = _memory_navigator.register_palace(nodes)
        return {"status": "OK", "palace_id": palace_id, "node_count": len(nodes)}
    except Exception as e:
        logger.error(f"Memory palace register failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neural/memory-palace/navigate")
async def memory_palace_navigate(request: MemoryPalaceNavigateRequest, user_id: str = Depends(require_verified_email)):
    try:
        node = _memory_navigator.navigate(request.palace_id, request.node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        return {
            "status": "OK",
            "node": {
                "node_id": node.node_id,
                "palace_id": node.palace_id,
                "label": node.label,
                "position": node.position,
                "connected_nodes": node.connected_nodes,
                "tags": node.tags,
                "memory_store": node.memory_store,
                "metadata": node.metadata,
                "timestamp": node.timestamp,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory palace navigate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/memory-palace/current")
async def memory_palace_current(user_id: str = Depends(require_verified_email)):
    try:
        palace = _memory_navigator.current_palace()
        if not palace:
            return {"status": "OK", "palace": None}
        return {
            "status": "OK",
            "palace": [
                {
                    "node_id": n.node_id,
                    "label": n.label,
                    "position": n.position,
                    "tags": n.tags,
                }
                for n in palace
            ],
        }
    except Exception as e:
        logger.error(f"Memory palace current failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Dream-state Assistant
# ============================================================================

@router.post("/neural/dream/assist")
async def dream_assist(request: DreamAssistRequest, user_id: str = Depends(require_verified_email)):
    try:
        epoch = _neural_api._simulate_epoch(
            [ElectrodeLocation[c] for c in request.channels] if request.channels else _neural_api._default_channels()
        )
        reading = _dream_assistant.assist(epoch)
        return {
            "status": "OK",
            "reading": {
                "reading_id": reading.reading_id,
                "hypnogram_stage": reading.hypnogram_stage,
                "nrem_sleep_ratio": reading.nrem_sleep_ratio,
                "rem_sleep_ratio": reading.rem_sleep_ratio,
                "sleep_onset_minutes": reading.sleep_onset_minutes,
                "dream_likelihood": reading.dream_likelihood,
                "dream_clarity": reading.dream_clarity,
                "lucid_dream_readiness": reading.lucid_dream_readiness,
                "assisted_actions": reading.assisted_actions,
                "timestamp": reading.timestamp,
            },
        }
    except Exception as e:
        logger.error(f"Dream assist failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/dream/history")
async def dream_history(limit: int = 50, user_id: str = Depends(require_verified_email)):
    try:
        history = _dream_assistant.recent()[:limit]
        return {
            "status": "OK",
            "history": [
                {
                    "reading_id": r.reading_id,
                    "hypnogram_stage": r.hypnogram_stage,
                    "rem_sleep_ratio": r.rem_sleep_ratio,
                    "dream_likelihood": r.dream_likelihood,
                    "dream_clarity": r.dream_clarity,
                    "lucid_dream_readiness": r.lucid_dream_readiness,
                    "timestamp": r.timestamp,
                }
                for r in history
            ],
        }
    except Exception as e:
        logger.error(f"Dream history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Lucid Dreaming Protocol
# ============================================================================

@router.post("/neural/dream/lucid/start")
async def lucid_start(request: LucidProtocolControlRequest, user_id: str = Depends(require_verified_email)):
    try:
        if request.active:
            _lucid_protocol.start_protocol()
        else:
            _lucid_protocol.stop_protocol()
        return {"status": "OK", "active": _lucid_protocol.active, "attempts": _lucid_protocol.attempts}
    except Exception as e:
        logger.error(f"Lucid protocol start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neural/dream/lucid/tick")
async def lucid_tick(request: DreamAssistRequest, user_id: str = Depends(require_verified_email)):
    try:
        epoch = _neural_api._simulate_epoch(
            [ElectrodeLocation[c] for c in request.channels] if request.channels else _neural_api._default_channels()
        )
        reading = _lucid_protocol.tick(epoch)
        if not reading:
            return {"status": "OK", "active": False, "reading": None}
        return {
            "status": "OK",
            "active": _lucid_protocol.active,
            "attempts": _lucid_protocol.attempts,
            "reading": {
                "reading_id": reading.reading_id,
                "hypnogram_stage": reading.hypnogram_stage,
                "dream_likelihood": reading.dream_likelihood,
                "dream_clarity": reading.dream_clarity,
                "lucid_dream_readiness": reading.lucid_dream_readiness,
                "assisted_actions": reading.assisted_actions,
                "timestamp": reading.timestamp,
            },
        }
    except Exception as e:
        logger.error(f"Lucid protocol tick failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Consciousness Readout Visualization
# ============================================================================

@router.post("/neural/consciousness/readout")
async def consciousness_readout(request: ConsciousnessReadoutRequest, user_id: str = Depends(require_verified_email)):
    try:
        epoch = _neural_api._simulate_epoch(
            [ElectrodeLocation[c] for c in request.channels] if request.channels else _neural_api._default_channels()
        )
        readout = _consciousness_engine.generate(epoch)
        readout.self_reported_clarity = request.self_reported_clarity
        return {
            "status": "OK",
            "readout": {
                "readout_id": readout.readout_id,
                "p300_detected": readout.p300_detected,
                "p300_latency_ms": readout.p300_latency_ms,
                "erp_components": readout.erp_components,
                "band_power_map": readout.band_power_map,
                "integrated_awareness": readout.integrated_awareness,
                "metacognition": readout.metacognition,
                "working_memory_load": readout.working_memory_load,
                "self_reported_clarity": readout.self_reported_clarity,
                "timestamp": readout.timestamp,
            },
        }
    except Exception as e:
        logger.error(f"Consciousness readout failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/consciousness/history")
async def consciousness_history(limit: int = 50, user_id: str = Depends(require_verified_email)):
    try:
        history = _consciousness_engine.recent()[:limit]
        return {
            "status": "OK",
            "history": [
                {
                    "readout_id": r.readout_id,
                    "p300_detected": r.p300_detected,
                    "p300_latency_ms": r.p300_latency_ms,
                    "integrated_awareness": r.integrated_awareness,
                    "metacognition": r.metacognition,
                    "working_memory_load": r.working_memory_load,
                    "timestamp": r.timestamp,
                }
                for r in history
            ],
        }
    except Exception as e:
        logger.error(f"Consciousness history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BCI Adapters
# ============================================================================

@router.post("/neural/bci/connect")
async def bci_connect(request: BCIConnectRequest, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.bci_adapters import BCIAdapterRegistry
        registry = BCIAdapterRegistry()
        result = registry.connect(request.device_id, request.device_type, request.sample_rate_hz)
        return {"status": "OK", "connection": result}
    except Exception as e:
        logger.error(f"BCI connect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neural/bci/disconnect")
async def bci_disconnect(device_id: str = "stub_device", user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.bci_adapters import BCIAdapterRegistry
        registry = BCIAdapterRegistry()
        result = registry.disconnect(device_id)
        return {"status": "OK", "connection": result}
    except Exception as e:
        logger.error(f"BCI disconnect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/bci/devices")
async def bci_devices(user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.bci_adapters import BCIAdapterRegistry
        registry = BCIAdapterRegistry()
        devices = registry.list_devices()
        return {"status": "OK", "devices": devices}
    except Exception as e:
        logger.error(f"BCI devices list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Neural Signal Processing Pipeline
# ============================================================================

@router.post("/neural/signal/process")
async def signal_process(request: SignalProcessRequest, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.signal_pipeline import SignalProcessingPipeline
        pipeline = SignalProcessingPipeline()
        result = pipeline.process(request.signal, pipeline_id=request.pipeline_id)
        return {"status": "OK", "result": result}
    except Exception as e:
        logger.error(f"Signal processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neural/signal/filter")
async def signal_filter(request: SignalProcessRequest, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.signal_pipeline import SignalProcessingPipeline
        pipeline = SignalProcessingPipeline()
        result = pipeline.filter(request.signal)
        return {"status": "OK", "result": result}
    except Exception as e:
        logger.error(f"Signal filter failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EEG / EMG / MEG Integration Stubs
# ============================================================================

@router.post("/neural/modality/acquire")
async def modality_acquire(request: EEGEMGMEGRequest, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.modality_integration import ModalityIntegrationService
        service = ModalityIntegrationService()
        result = service.acquire(request.modality, request.channels, request.sample_rate_hz)
        return {"status": "OK", "acquisition": result}
    except Exception as e:
        logger.error(f"Modality acquire failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/modality/{modality}/status")
async def modality_status(modality: str, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.modality_integration import ModalityIntegrationService
        service = ModalityIntegrationService()
        status = service.get_status(modality)
        return {"status": "OK", "modality_status": status}
    except Exception as e:
        logger.error(f"Modality status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Neural Decoder Models
# ============================================================================

@router.post("/neural/decoder/predict")
async def decoder_predict(request: DecoderModelRequest, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.decoder_models import DecoderModelService
        service = DecoderModelService()
        result = service.predict(request.model_type, request.input_data)
        return {"status": "OK", "prediction": result}
    except Exception as e:
        logger.error(f"Decoder predict failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/decoder/models")
async def decoder_models(user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.decoder_models import DecoderModelService
        service = DecoderModelService()
        models = service.list_models()
        return {"status": "OK", "models": models}
    except Exception as e:
        logger.error(f"Decoder models list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Brain-to-Computer Command Bridge
# ============================================================================

@router.post("/neural/bridge/command")
async def brain_bridge_command(request: BrainCommandRequest, user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.brain_bridge import BrainToComputerBridge
        bridge = BrainToComputerBridge()
        result = bridge.execute_command(request.command, request.parameters, request.confidence_threshold)
        return {"status": "OK", "execution": result}
    except Exception as e:
        logger.error(f"Brain bridge command failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neural/bridge/status")
async def brain_bridge_status(user_id: str = Depends(require_verified_email)):
    try:
        from app.futuristic_interfaces.brain_bridge import BrainToComputerBridge
        bridge = BrainToComputerBridge()
        status = bridge.get_status()
        return {"status": "OK", "bridge_status": status}
    except Exception as e:
        logger.error(f"Brain bridge status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
