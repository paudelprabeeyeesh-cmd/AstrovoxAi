from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
        from multimodal.audio_pipeline import AudioPipeline
        from multimodal.vision_pipeline import VisionPipeline

        self.audio_pipeline = AudioPipeline(sample_rate=sample_rate, n_mfcc=n_mfcc)
        self.vision_pipeline = VisionPipeline(feature_dim=feature_dim, num_regions=num_regions)

    def route(
        self,
        waveform=None,
        sample_rate: int = 16000,
        pixels=None,
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        if waveform is not None:
            results["audio"] = self.audio_pipeline.process(waveform, sample_rate)
        if pixels is not None:
            results["vision"] = self.vision_pipeline.process(pixels)
        return results

    def route_audio(self, waveform, sample_rate: int = 16000):
        from multimodal.audio_pipeline import AudioPipelineResult

        return self.audio_pipeline.process(waveform, sample_rate)

    def route_vision(self, pixels):
        from multimodal.vision_pipeline import VisionPipelineResult

        return self.vision_pipeline.process(pixels)

    def detect_modality(self, data) -> str:
        if hasattr(data, "tolist"):
            data = data.tolist()
        if isinstance(data, list):
            if not data:
                return "unknown"
            if isinstance(data[0], (int, float)):
                return "audio"
            if isinstance(data[0], list):
                if not data[0]:
                    return "unknown"
                if isinstance(data[0][0], (int, float)):
                    return "vision"
                if isinstance(data[0][0], list):
                    return "vision"
            return "unknown"
        if isinstance(data, str):
            return "text"
        return "unknown"
