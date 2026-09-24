import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class GenerationConfig:
    text: str
    modality: str
    seed: Optional[int] = None
    num_steps: int = 10
    guidance_scale: float = 7.5
    output_shape: Optional[Tuple[int, ...]] = None


class TextToImageGenerator:
    def __init__(self, image_size: int = 64, latent_dim: int = 128):
        self.image_size = image_size
        self.latent_dim = latent_dim
        self._rng = np.random.default_rng(42)
        self.W_text = self._rng.standard_normal((256, latent_dim)) * 0.02
        self.W_decoder = self._rng.standard_normal((latent_dim, image_size * image_size * 3)) * 0.02

    def encode_text(self, text: str) -> np.ndarray:
        vec = np.zeros(256, dtype=np.float64)
        tokens = text.lower().split()
        for idx, token in enumerate(tokens):
            h = hash(token) % 256
            vec[h] += 1.0
            vec[(h + 1) % 256] += 0.5 * (idx + 1) / len(tokens)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def generate(self, config: GenerationConfig) -> np.ndarray:
        text_emb = self.encode_text(config.text)
        seed = config.seed if config.seed is not None else 42
        rng = np.random.default_rng(seed)
        z = rng.standard_normal(self.latent_dim)
        z = self._classifier_free_guidance(z, text_emb, config.guidance_scale, rng)
        for step in range(config.num_steps):
            z = self._denoise_step(z, text_emb, step / config.num_steps, rng)
        image = self._decode_latent(z)
        return np.clip(image, 0, 255).astype(np.uint8)

    def _classifier_free_guidance(self, z: np.ndarray, text_emb: np.ndarray, scale: float, rng: np.random.Generator) -> np.ndarray:
        noise = rng.standard_normal(self.latent_dim)
        guided = z + scale * (text_emb @ self.W_text).mean()
        return (1 - 1 / scale) * noise + (1 / scale) * guided

    def _denoise_step(self, z: np.ndarray, text_emb: np.ndarray, t: float, rng: np.random.Generator) -> np.ndarray:
        noise_pred = rng.standard_normal(self.latent_dim) * (1 - t)
        text_cond = (text_emb @ self.W_text).mean()
        z = z - (noise_pred + text_cond) * (1 - t) * 0.1
        return np.clip(z, -3, 3)

    def _decode_latent(self, z: np.ndarray) -> np.ndarray:
        image_flat = z @ self.W_decoder
        image_flat = (image_flat - image_flat.min()) / (image_flat.max() - image_flat.min() + 1e-8) * 255
        return image_flat.reshape(self.image_size, self.image_size, 3)


class TextToSpeechSynthesizer:
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        self._rng = np.random.default_rng(42)
        self.phoneme_durations = {
            "a": 0.08, "e": 0.07, "i": 0.06, "o": 0.08, "u": 0.07,
            "p": 0.05, "t": 0.04, "k": 0.05, "m": 0.08, "n": 0.07,
            "s": 0.06, "l": 0.07, "r": 0.06, " ": 0.1,
        }

    def synthesize(self, text: str, pitch: float = 1.0, speed: float = 1.0) -> np.ndarray:
        phonemes = self._text_to_phonemes(text)
        samples = []
        for phoneme in phonemes:
            dur = self.phoneme_durations.get(phoneme, 0.07) / speed
            num_samples = int(dur * self.sample_rate)
            t = np.linspace(0, dur, num_samples, endpoint=False)
            freq = 150 * pitch * (1 + 0.01 * hash(phoneme) % 5)
            phase = np.sin(2 * np.pi * freq * t + self._rng.standard_normal() * 0.1)
            envelope = np.hanning(num_samples)
            samples.append(phase * envelope)
        waveform = np.concatenate(samples) if samples else np.zeros(int(0.5 * self.sample_rate))
        return waveform / (np.max(np.abs(waveform)) + 1e-8)

    def _text_to_phonemes(self, text: str) -> List[str]:
        phoneme_map = {
            "h": "a", "e": "e", "l": "l", "o": "o", " ": " ",
            "w": "u", "r": "r", "d": "t", "s": "s", "i": "i",
            "g": "k", "n": "n", "m": "m", "p": "p", "t": "t",
        }
        return [phoneme_map.get(ch.lower(), "a") for ch in text if ch.isalnum() or ch == " "]


class TextToVideoGenerator:
    def __init__(self, num_frames: int = 16, frame_size: int = 32, latent_dim: int = 64):
        self.num_frames = num_frames
        self.frame_size = frame_size
        self.latent_dim = latent_dim
        self._rng = np.random.default_rng(42)
        self.W_temporal = self._rng.standard_normal((latent_dim, latent_dim)) * 0.02
        self.W_spatial = self._rng.standard_normal((latent_dim, frame_size * frame_size * 3)) * 0.02

    def encode_text(self, text: str) -> np.ndarray:
        vec = np.zeros(self.latent_dim, dtype=np.float64)
        tokens = text.lower().split()
        for idx, token in enumerate(tokens):
            h = hash(token) % self.latent_dim
            vec[h] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def generate(self, text: str, num_steps: int = 8, fps: int = 8) -> np.ndarray:
        text_emb = self.encode_text(text)
        rng = np.random.default_rng(42)
        z = rng.standard_normal((self.num_frames, self.latent_dim))
        z = self._apply_temporal_attention(z, text_emb)
        for step in range(num_steps):
            z = self._denoise_temporal(z, text_emb, step / num_steps)
        frames = self._decode_frames(z)
        return frames

    def _apply_temporal_attention(self, z: np.ndarray, text_emb: np.ndarray) -> np.ndarray:
        text_influence = (text_emb @ self.W_temporal).reshape(1, -1)
        return z + 0.1 * text_influence

    def _denoise_temporal(self, z: np.ndarray, text_emb: np.ndarray, t: float) -> np.ndarray:
        noise = self._rng.standard_normal(z.shape) * (1 - t)
        text_cond = (text_emb @ self.W_temporal).reshape(1, -1)
        z = z - (noise + np.tile(text_cond, (z.shape[0], 1))) * (1 - t) * 0.1
        return np.clip(z, -3, 3)

    def _decode_frames(self, z: np.ndarray) -> np.ndarray:
        frames = []
        for t in range(z.shape[0]):
            frame_flat = z[t] @ self.W_spatial
            frame_flat = (frame_flat - frame_flat.min()) / (frame_flat.max() - frame_flat.min() + 1e-8) * 255
            frames.append(frame_flat.reshape(self.frame_size, self.frame_size, 3).astype(np.uint8))
        return np.array(frames)
