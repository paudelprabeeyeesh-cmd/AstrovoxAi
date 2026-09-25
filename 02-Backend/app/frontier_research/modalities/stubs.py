"""VLM, speech, video, edge, and accelerator stubs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VLMInput:
    image: Any
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VLMOutput:
    text: str
    embeddings: list[float] = field(default_factory=list)


class VLMStub:
    def __init__(self, model_id: str = "mock-vlm"):
        self.model_id = model_id

    def forward(self, inputs: VLMInput) -> VLMOutput:
        logger.debug("VLM stub forward for model %s", self.model_id)
        return VLMOutput(text="[VLM stub output]")


@dataclass
class SpeechInput:
    audio: Any
    sample_rate: int = 16000
    language: str = "en"


@dataclass
class SpeechOutput:
    text: str
    confidence: float = 0.0


class SpeechStub:
    def __init__(self, model_id: str = "mock-whisper"):
        self.model_id = model_id

    def transcribe(self, inputs: SpeechInput) -> SpeechOutput:
        logger.debug("Speech stub transcribe for model %s", self.model_id)
        return SpeechOutput(text="[speech stub output]", confidence=0.0)

    def synthesize(self, text: str, voice: str = "default") -> SpeechOutput:
        logger.debug("Speech stub synthesize for model %s", self.model_id)
        return SpeechOutput(text=text, confidence=0.0)


@dataclass
class VideoInput:
    frames: list[Any]
    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoOutput:
    summary: str
    events: list[dict[str, Any]] = field(default_factory=list)


class VideoStub:
    def __init__(self, model_id: str = "mock-video"):
        self.model_id = model_id

    def forward(self, inputs: VideoInput) -> VideoOutput:
        logger.debug("Video stub forward for model %s", self.model_id)
        return VideoOutput(summary="[video stub output]")


@dataclass
class EdgeConfig:
    target: str = "cpu"
    max_batch_size: int = 1
    quantized: bool = False


class EdgeStub:
    def __init__(self, config: EdgeConfig | None = None):
        self.config = config or EdgeConfig()

    def optimize(self, model: Any) -> Any:
        logger.debug("Edge stub optimizing model for %s", self.config.target)
        return model


@dataclass
class AcceleratorConfig:
    accelerator: str = "cpu"
    precision: str = "fp32"
    device_index: int = 0


class AcceleratorStub:
    def __init__(self, config: AcceleratorConfig | None = None):
        self.config = config or AcceleratorConfig()

    def allocate(self, model: Any) -> Any:
        logger.debug("Accelerator stub allocating model on %s:%s", self.config.accelerator, self.config.device_index)
        return model
