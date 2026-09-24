import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from multimodal.audio_language import AudioFeatures, AudioLanguageModel


@dataclass
class AudioPipelineResult:
    features: AudioFeatures
    transcription: str
    snr: float
    pesq: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AudioPipeline:
    def __init__(self, sample_rate: int = 16000, n_mfcc: int = 13):
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.model = AudioLanguageModel(sample_rate=sample_rate, n_mfcc=n_mfcc)

    def process(self, waveform: np.ndarray, sample_rate: int) -> AudioPipelineResult:
        feats = self.model.load_audio(waveform, sample_rate)
        transcription = self.model.transcribe(feats)
        snr = self.model.compute_snr(feats.waveform, feats.waveform)
        pesq = self.model.compute_pesq_like(feats.waveform, feats.waveform)
        return AudioPipelineResult(
            features=feats,
            transcription=transcription,
            snr=snr,
            pesq=pesq,
            metadata={
                "sample_rate": feats.sample_rate,
                "duration": feats.duration,
            },
        )
