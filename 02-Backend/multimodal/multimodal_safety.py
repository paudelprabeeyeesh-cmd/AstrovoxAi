import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class SafetyResult:
    is_safe: bool
    toxicity_score: float
    bias_score: float
    deepfake_probability: float
    flags: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class ContentModerator:
    def __init__(self):
        self._rng = np.random.default_rng(42)
        self.toxicity_lexicon = self._build_toxicity_lexicon()

    def _build_toxicity_lexicon(self) -> Dict[str, float]:
        return {
            "hate": 0.9, "violence": 0.8, "harm": 0.7, "kill": 0.9,
            "attack": 0.6, "abuse": 0.7, "threat": 0.8, "insult": 0.5,
            "profanity": 0.6, "discriminatory": 0.7, "racist": 0.9,
            "sexist": 0.8, "harassment": 0.7, "explicit": 0.6,
        }

    def moderate_text(self, text: str) -> Dict[str, Any]:
        tokens = text.lower().split()
        toxicity = 0.0
        flagged = []
        for token in tokens:
            if token in self.toxicity_lexicon:
                score = self.toxicity_lexicon[token]
                toxicity = max(toxicity, score)
                flagged.append(token)
        bias = self._detect_bias(text)
        return {
            "toxicity_score": toxicity,
            "bias_score": bias,
            "flagged_terms": flagged,
            "is_toxic": toxicity > 0.5,
        }

    def _detect_bias(self, text: str) -> float:
        bias_indicators = ["all", "always", "never", "every", "none", "only"]
        tokens = text.lower().split()
        count = sum(1 for t in tokens if t in bias_indicators)
        return min(count / max(len(tokens), 1), 1.0)

    def moderate_image(self, pixels: np.ndarray) -> Dict[str, Any]:
        if pixels.ndim == 3:
            gray = pixels.mean(axis=2)
        else:
            gray = pixels
        explicit_score = self._detect_explicit_content(gray)
        nsfw_score = self._detect_nsfw(gray)
        return {
            "explicit_score": explicit_score,
            "nsfw_score": nsfw_score,
            "is_explicit": explicit_score > 0.5,
        }

    def _detect_explicit_content(self, gray: np.ndarray) -> float:
        edges = self._sobel_edges(gray)
        edge_density = np.mean(edges > 0.5)
        hist, _ = np.histogram(gray, bins=16, density=True)
        contrast = np.std(hist)
        return float(np.clip(edge_density * 0.5 + contrast * 0.5, 0, 1))

    def _detect_nsfw(self, gray: np.ndarray) -> float:
        skin_mask = ((gray > 95) & (gray < 150)).astype(float)
        skin_ratio = np.mean(skin_mask)
        return float(np.clip(skin_ratio * 2.0, 0, 1))

    def _sobel_edges(self, gray: np.ndarray) -> np.ndarray:
        Kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
        Ky = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]], dtype=np.float64)
        Gx = self._convolve2d(gray, Kx)
        Gy = self._convolve2d(gray, Ky)
        return np.sqrt(Gx ** 2 + Gy ** 2)

    def _convolve2d(self, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        kh, kw = kernel.shape
        h, w = image.shape
        output = np.zeros_like(image)
        for i in range(kh // 2, h - kh // 2):
            for j in range(kw // 2, w - kw // 2):
                output[i, j] = np.sum(image[i - kh // 2:i + kh // 2 + 1, j - kw // 2:j + kw // 2 + 1] * kernel)
        return output


class DeepfakeDetector:
    def __init__(self):
        self._rng = np.random.default_rng(42)

    def detect_image(self, pixels: np.ndarray) -> Dict[str, Any]:
        if pixels.ndim == 3:
            gray = pixels.mean(axis=2)
        else:
            gray = pixels
        freq_features = self._extract_frequency_features(gray)
        inconsistency = self._check_spatial_inconsistency(gray)
        noise_pattern = self._analyze_noise_pattern(gray)
        score = 0.4 * freq_features + 0.35 * inconsistency + 0.25 * noise_pattern
        return {
            "deepfake_probability": float(np.clip(score, 0, 1)),
            "frequency_anomaly": float(freq_features),
            "spatial_inconsistency": float(inconsistency),
            "noise_anomaly": float(noise_pattern),
            "is_deepfake": score > 0.5,
        }

    def _extract_frequency_features(self, gray: np.ndarray) -> float:
        fft = np.fft.fft2(gray)
        magnitude = np.abs(np.fft.fftshift(fft))
        h, w = magnitude.shape
        center_h, center_w = h // 2, w // 2
        low_freq = magnitude[center_h - 10:center_h + 10, center_w - 10:center_w + 10]
        high_freq = magnitude.copy()
        high_freq[center_h - 30:center_h + 30, center_w - 30:center_w + 30] = 0
        low_energy = np.mean(low_freq)
        high_energy = np.mean(high_freq)
        if low_energy == 0:
            return 0.0
        return float(np.clip(high_energy / low_energy, 0, 1))

    def _check_spatial_inconsistency(self, gray: np.ndarray) -> float:
        h, w = gray.shape
        blocks = []
        for i in range(0, h, h // 4):
            for j in range(0, w, w // 4):
                block = gray[i:i + h // 4, j:j + w // 4]
                if block.size > 0:
                    blocks.append(block)
        if len(blocks) < 2:
            return 0.0
        means = [np.mean(b) for b in blocks]
        std_means = np.std(means)
        return float(np.clip(std_means / 128.0, 0, 1))

    def _analyze_noise_pattern(self, gray: np.ndarray) -> float:
        laplacian = self._laplacian(gray)
        noise_estimate = np.std(laplacian)
        return float(np.clip(noise_estimate / 50.0, 0, 1))

    def _laplacian(self, gray: np.ndarray) -> np.ndarray:
        kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=np.float64)
        return self._convolve2d(gray, kernel)

    def _convolve2d(self, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        kh, kw = kernel.shape
        h, w = image.shape
        output = np.zeros_like(image)
        for i in range(kh // 2, h - kh // 2):
            for j in range(kw // 2, w - kw // 2):
                output[i, j] = np.sum(image[i - kh // 2:i + kh // 2 + 1, j - kw // 2:j + kw // 2 + 1] * kernel)
        return output


class MultimodalSafetySystem:
    def __init__(self):
        self.moderator = ContentModerator()
        self.deepfake_detector = DeepfakeDetector()

    def evaluate(self, text: Optional[str] = None, image: Optional[np.ndarray] = None, audio_waveform: Optional[np.ndarray] = None) -> SafetyResult:
        flags = []
        toxicity_score = 0.0
        bias_score = 0.0
        deepfake_prob = 0.0

        if text:
            text_result = self.moderator.moderate_text(text)
            toxicity_score = max(toxicity_score, text_result["toxicity_score"])
            bias_score = max(bias_score, text_result["bias_score"])
            if text_result["is_toxic"]:
                flags.extend(text_result["flagged_terms"])

        if image is not None:
            img_result = self.moderator.moderate_image(image)
            deepfake_result = self.deepfake_detector.detect_image(image)
            if img_result["is_explicit"]:
                flags.append("explicit_content")
            deepfake_prob = max(deepfake_prob, deepfake_result["deepfake_probability"])
            if deepfake_result["is_deepfake"]:
                flags.append("deepfake_detected")

        is_safe = toxicity_score < 0.5 and len(flags) == 0 and deepfake_prob < 0.5
        return SafetyResult(
            is_safe=is_safe,
            toxicity_score=toxicity_score,
            bias_score=bias_score,
            deepfake_probability=deepfake_prob,
            flags=flags,
        )
