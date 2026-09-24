import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from multimodal.audio_pipeline import AudioPipeline, AudioPipelineResult
from multimodal.vision_pipeline import VisionPipeline, VisionPipelineResult


@dataclass
class RoutingDecision:
    modality: str
    confidence: float
    processor: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModalityRouter:
    def __init__(
        self,
        sample_rate: int = 16000,
        n_mfcc: int = 13,
        feature_dim: int = 256,
        num_regions: int = 9,
    ):
        self.audio_pipeline = AudioPipeline(sample_rate=sample_rate, n_mfcc=n_mfcc)
        self.vision_pipeline = VisionPipeline(feature_dim=feature_dim, num_regions=num_regions)

    def route(
        self,
        waveform: Optional[np.ndarray] = None,
        sample_rate: int = 16000,
        pixels: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        if waveform is not None:
            results["audio"] = self.audio_pipeline.process(waveform, sample_rate)
        if pixels is not None:
            results["vision"] = self.vision_pipeline.process(pixels)
        return results

    def route_audio(
        self,
        waveform: np.ndarray,
        sample_rate: int = 16000,
    ) -> AudioPipelineResult:
        return self.audio_pipeline.process(waveform, sample_rate)

    def route_vision(
        self,
        pixels: np.ndarray,
    ) -> VisionPipelineResult:
        return self.vision_pipeline.process(pixels)

    def detect_modality(self, data: Any) -> str:
        if isinstance(data, np.ndarray):
            if data.ndim == 1:
                return "audio"
            if data.ndim == 2:
                return "vision"
            if data.ndim == 3:
                return "vision"
            return "unknown"
        if isinstance(data, str):
            return "text"
        return "unknown"
