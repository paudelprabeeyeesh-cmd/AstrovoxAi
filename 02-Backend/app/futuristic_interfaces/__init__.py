
import asyncio
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional


class ElectrodeLocation(str, Enum):
    FP1 = "FP1"
    FP2 = "FP2"
    F3 = "F3"
    F4 = "F4"
    C3 = "C3"
    C4 = "C4"
    P3 = "P3"
    P4 = "P4"
    O1 = "O1"
    O2 = "O2"
    FZ = "Fz"
    CZ = "Cz"
    PZ = "Pz"
    OZ = "Oz"


class SignalQuality(str, Enum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    NO_SIGNAL = "no_signal"


class BandPower(str, Enum):
    DELTA = "delta"
    THETA = "theta"
    ALPHA = "alpha"
    BETA = "beta"
    GAMMA = "gamma"


@dataclass
class PowerBand:
    electrode: ElectrodeLocation
    band: BandPower
    power: float
    relative_power: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class DecodingPipeline:
    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sample_rate_hz: float = 250.0
    epoch_duration_ms: int = 200
    notch_filter_hz: Optional[float] = 60.0
    band_pass_hz: tuple = (1.0, 80.0)
    features: List[str] = field(
        default_factory=lambda: ["band_power", "hoc", "wsm", "asymmetry", "coherence"]
    )
    artifact_rejection: bool = True
    bad_channel_threshold_std: float = 3.0


@dataclass
class NeuralSignal:
    epoch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channels: List[ElectrodeLocation] = field(
        default_factory=lambda: list(ElectrodeLocation)
    )
    samples: List[List[float]] = field(default_factory=list)
    sample_rate_hz: float = 250.0
    power_bands: List[PowerBand] = field(default_factory=list)
    artifacts_rejected: int = 0
    signal_quality: SignalQuality = SignalQuality.GOOD
    pipeline_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class MotorImageryCommand:
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    epoch_id: str = ""
    predicted_class: str = "rest"
    confidence: float = 0.0
    features: Dict[str, Any] = field(default_factory=dict)
    command_chain: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class EmotionReading:
    reading_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    epoch_id: str = ""
    dominant_emotion: str = "neutral"
    valence: float = 0.0
    arousal: float = 0.0
    emotion_scores: Dict[str, float] = field(default_factory=dict)
    signal_quality: SignalQuality = SignalQuality.GOOD
    timestamp: float = field(default_factory=time.time)


@dataclass
class NeurofeedbackMetric:
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metric: str = "alpha_power"
    value: float = 0.0
    target_range: tuple = (0.0, 0.0)
    unit: str = ""
    quality: SignalQuality = SignalQuality.GOOD
    electrode: Optional[ElectrodeLocation] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class MemoryPalaceNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    palace_id: str = ""
    label: str = ""
    position: tuple = (0.0, 0.0, 0.0)
    connected_nodes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    memory_store: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DreamStateReading:
    reading_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hypnogram_stage: str = "N1"
    nrem_sleep_ratio: float = 0.0
    rem_sleep_ratio: float = 0.0
    sleep_onset_minutes: float = 0.0
    dream_likelihood: float = 0.0
    dream_clarity: float = 0.0
    lucid_dream_readiness: float = 0.0
    assisted_actions: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConsciousnessReadout:
    readout_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    p300_detected: bool = False
    p300_latency_ms: Optional[float] = None
    erp_components: Dict[str, float] = field(default_factory=dict)
    band_power_map: Dict[str, Any] = field(default_factory=dict)
    integrated_awareness: float = 0.0
    metacognition: float = 0.0
    working_memory_load: float = 0.0
    self_reported_clarity: Optional[float] = None
    timestamp: float = field(default_factory=time.time)


def _simulate_power_band(electrode: ElectrodeLocation, band: BandPower, noise: float = 0.05) -> PowerBand:
    center = {
        BandPower.DELTA: 0.4,
        BandPower.THETA: 0.2,
        BandPower.ALPHA: 0.25,
        BandPower.BETA: 0.1,
        BandPower.GAMMA: 0.05,
    }[band]
    power = max(0.0, random.gauss(center, noise))
    return PowerBand(electrode=electrode, band=band, power=power, relative_power=power)


def _simulate_epoch(channels: List[ElectrodeLocation]) -> NeuralSignal:
    sample_count = 50
    samples: List[List[float]] = []
    for _ in range(len(channels)):
        samples.append([random.gauss(0.0, 1.0) for _ in range(sample_count)])

    power_bands: List[PowerBand] = []
    for channel in channels:
        for band in BandPower:
            power_bands.append(_simulate_power_band(channel, band))

    return NeuralSignal(
        channels=channels,
        samples=samples,
        power_bands=power_bands,
        signal_quality=random.choice(list(SignalQuality)),
    )


class NeuralSignalAPI:
    def __init__(self, device_id: Optional[str] = None) -> None:
        self.device_id = device_id or str(uuid.uuid4())
        self.pipelines: Dict[str, DecodingPipeline] = {}
        self.epochs: Dict[str, NeuralSignal] = {}
        self._listeners: List[Callable[[NeuralSignal], Awaitable[None]]] = []
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

    async def start(self, pipeline_id: str) -> None:
        if pipeline_id not in self.pipelines:
            raise KeyError(f"Unknown pipeline_id={pipeline_id}")
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._stream_epochs(pipeline_id))

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def add_listener(self, listener: Callable[[NeuralSignal], Awaitable[None]]) -> None:
        self._listeners.append(listener)

    def _default_channels(self) -> List[ElectrodeLocation]:
        return [
            ElectrodeLocation.FP1,
            ElectrodeLocation.FP2,
            ElectrodeLocation.F3,
            ElectrodeLocation.F4,
            ElectrodeLocation.C3,
            ElectrodeLocation.C4,
            ElectrodeLocation.P3,
            ElectrodeLocation.P4,
            ElectrodeLocation.O1,
            ElectrodeLocation.O2,
        ]

    async def _stream_epochs(self, pipeline_id: str) -> None:
        pipeline = self.pipelines[pipeline_id]
        interval = pipeline.epoch_duration_ms / 1000.0
        while self._running:
            epoch = _simulate_epoch(self._default_channels())
            epoch.pipeline_id = pipeline_id
            self.epochs[epoch.epoch_id] = epoch
            for listener in self._listeners:
                asyncio.create_task(self._safe_listener(listener, epoch))
            await asyncio.sleep(interval)

    async def _safe_listener(self, listener: Callable[[NeuralSignal], Awaitable[None]], epoch: NeuralSignal) -> None:
        try:
            await listener(epoch)
        except Exception:
            pass

    def create_pipeline(self, pipeline: DecodingPipeline) -> str:
        self.pipelines[pipeline.pipeline_id] = pipeline
        return pipeline.pipeline_id

    async def get_recent_epochs(self, count: int = 20) -> List[NeuralSignal]:
        items = sorted(self.epochs.values(), key=lambda e: e.timestamp, reverse=True)
        return items[:count]


class MotorImageryDecoder:
    def __init__(self) -> None:
        self._commands: Dict[str, MotorImageryCommand] = {}

    def predict(self, epoch: NeuralSignal) -> MotorImageryCommand:
        commands = [
            "left_hand", "right_hand", "feet", "tongue", "rest",
            "turn_left", "turn_right", "forward", "backward",
        ]
        predicted = random.choice(commands)
        confidence = random.uniform(0.5, 0.99)
        command = MotorImageryCommand(
            epoch_id=epoch.epoch_id,
            predicted_class=predicted,
            confidence=confidence,
            features={"theta_over_beta": random.uniform(0.0, 1.0)},
        )
        self._commands[command.command_id] = command
        return command

    def history(self) -> List[MotorImageryCommand]:
        return sorted(self._commands.values(), key=lambda c: c.timestamp, reverse=True)


class EmotionDecoder:
    def __init__(self) -> None:
        self._readings: Dict[str, EmotionReading] = {}

    def predict(self, epoch: NeuralSignal) -> EmotionReading:
        scores = {
            "joy": random.uniform(0.0, 0.8),
            "sadness": random.uniform(0.0, 0.8),
            "anger": random.uniform(0.0, 0.8),
            "fear": random.uniform(0.0, 0.8),
            "disgust": random.uniform(0.0, 0.8),
            "surprise": random.uniform(0.0, 0.8),
            "neutral": random.uniform(0.0, 0.8),
        }
        dominant = max(scores, key=scores.get)
        reading = EmotionReading(
            epoch_id=epoch.epoch_id,
            dominant_emotion=dominant,
            valence=random.uniform(-1.0, 1.0),
            arousal=random.uniform(0.0, 1.0),
            emotion_scores=scores,
        )
        self._readings[reading.reading_id] = reading
        return reading

    def recent(self) -> List[EmotionReading]:
        return sorted(self._readings.values(), key=lambda r: r.timestamp, reverse=True)


class MemoryPalaceNavigator:
    def __init__(self) -> None:
        self.palaces: Dict[str, List[MemoryPalaceNode]] = {}
        self.navigation_history: List[str] = []

    def register_palace(self, nodes: List[MemoryPalaceNode]) -> str:
        palace_id = nodes[0].palace_id or str(uuid.uuid4())
        for node in nodes:
            node.palace_id = palace_id
        self.palaces[palace_id] = nodes
        return palace_id

    def navigate(self, palace_id: str, node_id: str) -> Optional[MemoryPalaceNode]:
        nodes = self.palaces.get(palace_id) or []
        for node in nodes:
            if node.node_id == node_id:
                self.navigation_history.append(node_id)
                return node
        return None

    def current_palace(self) -> Optional[List[MemoryPalaceNode]]:
        if not self.palaces:
            return None
        return self.palaces[list(self.palaces.keys())[-1]]


class DreamStateAssistant:
    def __init__(self) -> None:
        self.readings: List[DreamStateReading] = []

    def assist(self, epoch: NeuralSignal) -> DreamStateReading:
        reading = DreamStateReading(
            hypnogram_stage=random.choice(["N1", "N2", "N3", "REM", "Wake"]),
            rem_sleep_ratio=random.uniform(0.0, 0.5),
            nrem_sleep_ratio=random.uniform(0.0, 0.7),
            dream_likelihood=random.uniform(0.0, 1.0),
            dream_clarity=random.uniform(0.0, 1.0),
            lucid_dream_readiness=random.uniform(0.0, 1.0),
            assisted_actions=[],
        )
        self.readings.append(reading)
        return reading

    def recent(self) -> List[DreamStateReading]:
        return self.readings[-50:]


class LucidDreamingProtocol:
    def __init__(self, assistant: DreamStateAssistant) -> None:
        self.assistant = assistant
        self.active: bool = False
        self.attempts: int = 0

    def start_protocol(self) -> None:
        self.active = True
        self.attempts = 0

    def stop_protocol(self) -> None:
        self.active = False

    def tick(self, epoch: NeuralSignal) -> Optional[DreamStateReading]:
        if not self.active:
            return None
        self.attempts += 1
        reading = self.assistant.assist(epoch)
        reading.assisted_actions = [
            "mILD_induction",
            "reality_check",
            "stabilization_cue",
        ]
        return reading


class ConsciousnessReadoutEngine:
    def __init__(self) -> None:
        self.readouts: List[ConsciousnessReadout] = []

    def generate(self, epoch: NeuralSignal) -> ConsciousnessReadout:
        erp = {
            "P300": random.uniform(0.0, 1.0),
            "N400": random.uniform(0.0, 1.0),
            "MMN": random.uniform(0.0, 1.0),
            "N2": random.uniform(0.0, 1.0),
        }
        readout = ConsciousnessReadout(
            p300_detected=bool(random.getrandbits(1)),
            p300_latency_ms=random.uniform(250.0, 450.0),
            erp_components=erp,
            band_power_map={
                band.value: {channel.value: random.uniform(0.0, 1.0)
                             for channel in ElectrodeLocation}
                for band in BandPower
            },
            integrated_awareness=random.uniform(0.0, 1.0),
            metacognition=random.uniform(0.0, 1.0),
            working_memory_load=random.uniform(0.0, 1.0),
        )
        self.readouts.append(readout)
        return readout

    def recent(self) -> List[ConsciousnessReadout]:
        return self.readouts[-50:]
