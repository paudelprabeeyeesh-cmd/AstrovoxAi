import os
import sys
import logging
import numpy as np
import torch
import torch.nn as nn
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioEncoder(nn.Module):
    def __init__(self, input_dim: int = 128, hidden_dim: int = 256, output_dim: int = 128):
        super().__init__()
        self.conv1 = nn.Conv1d(input_dim, hidden_dim, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(hidden_dim, hidden_dim, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Linear(hidden_dim, output_dim)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.pool(x).squeeze(-1)
        return self.fc(x)


class AudioFeatureExtractor:
    def __init__(self):
        self.encoder = AudioEncoder()
        self.encoder.eval()

    def extract(self, audio_data: np.ndarray) -> np.ndarray:
        try:
            import librosa
            if audio_data.ndim > 1:
                audio_data = np.mean(audio_data, axis=1)
            mel = librosa.feature.melspectrogram(y=audio_data, sr=22050, n_mels=128)
            mel_db = librosa.power_to_db(mel, ref=np.max)
            mel_tensor = torch.from_numpy(mel_db).float().unsqueeze(0)
            with torch.no_grad():
                features = self.encoder(mel_tensor).squeeze().numpy()
            return features / (np.linalg.norm(features) + 1e-8)
        except Exception as exc:
            logger.warning(f"Feature extraction failed: {exc}")
            return np.zeros(128, dtype=np.float32)


class AudioAugmentor:
    @staticmethod
    def time_stretch(audio_data: np.ndarray, rate: float = 1.2) -> np.ndarray:
        try:
            import librosa
            return librosa.effects.time_stretch(audio_data, rate=rate)
        except Exception:
            return audio_data

    @staticmethod
    def pitch_shift(audio_data: np.ndarray, sr: int, n_steps: int = 2) -> np.ndarray:
        try:
            import librosa
            return librosa.effects.pitch_shift(audio_data, sr=sr, n_steps=n_steps)
        except Exception:
            return audio_data

    @staticmethod
    def add_noise(audio_data: np.ndarray, noise_level: float = 0.01) -> np.ndarray:
        noise = np.random.normal(0, noise_level, audio_data.shape)
        return audio_data + noise

    @staticmethod
    def random_gain(audio_data: np.ndarray, min_gain: float = 0.5, max_gain: float = 1.5) -> np.ndarray:
        gain = np.random.uniform(min_gain, max_gain)
        return audio_data * gain


class AudioUtils:
    @staticmethod
    def load_audio(path: str, sr: int = 22050) -> tuple[np.ndarray, int]:
        import soundfile as sf
        data, sample_rate = sf.read(path)
        if sample_rate != sr:
            import librosa
            data, _ = librosa.resample(data, orig_sr=sample_rate, target_sr=sr)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        return data.astype(np.float32), sr

    @staticmethod
    def save_audio(path: str, audio_data: np.ndarray, sr: int = 22050) -> None:
        import soundfile as sf
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(path, audio_data, sr)

    @staticmethod
    def normalize(audio_data: np.ndarray) -> np.ndarray:
        peak = np.max(np.abs(audio_data))
        if peak > 0:
            audio_data = audio_data / peak
        return audio_data
