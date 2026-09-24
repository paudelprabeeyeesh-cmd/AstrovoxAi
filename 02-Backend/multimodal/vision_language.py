import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class ImageFeatures:
    pixels: np.ndarray
    features: np.ndarray
    regions: List[Tuple[int, int, int, int]]
    spatial_pyramid: Optional[np.ndarray] = None


class VisionLanguageModel:
    def __init__(self, feature_dim: int = 256, num_regions: int = 9):
        self.feature_dim = feature_dim
        self.num_regions = num_regions
        self._rng = np.random.default_rng(42)

    def encode_image(self, pixels: np.ndarray) -> ImageFeatures:
        h, w = pixels.shape[:2]
        if pixels.ndim == 2:
            pixels = np.stack([pixels, pixels, pixels], axis=-1)
        regions = self._propose_regions(h, w)
        features = self._extract_region_features(pixels, regions)
        spatial_pyramid = self._build_spatial_pyramid(pixels)
        return ImageFeatures(
            pixels=pixels,
            features=features,
            regions=regions,
            spatial_pyramid=spatial_pyramid,
        )

    def _propose_regions(self, h: int, w: int) -> List[Tuple[int, int, int, int]]:
        grid = int(np.ceil(np.sqrt(self.num_regions)))
        rh, rw = max(1, h // grid), max(1, w // grid)
        regions = []
        for i in range(grid):
            for j in range(grid):
                y1, x1 = i * rh, j * rw
                y2, x2 = min((i + 1) * rh, h), min((j + 1) * rw, w)
                regions.append((y1, x1, y2, x2))
        return regions[: self.num_regions]

    def _extract_region_features(self, pixels: np.ndarray, regions: List[Tuple[int, int, int, int]]) -> np.ndarray:
        feats = []
        for (y1, x1, y2, x2) in regions:
            patch = pixels[y1:y2, x1:x2]
            if patch.size == 0:
                feats.append(np.zeros(self.feature_dim))
            else:
                feats.append(self._patch_to_vector(patch))
        return np.array(feats, dtype=np.float64)

    def _patch_to_vector(self, patch: np.ndarray) -> np.ndarray:
        hist_r, _ = np.histogram(patch[:, :, 0], bins=16, range=(0, 255), density=True)
        hist_g, _ = np.histogram(patch[:, :, 1], bins=16, range=(0, 255), density=True)
        hist_b, _ = np.histogram(patch[:, :, 2], bins=16, range=(0, 255), density=True)
        stats = np.array([patch.mean(), patch.std(), patch.min(), patch.max()], dtype=np.float64)
        vec = np.concatenate([hist_r, hist_g, hist_b, stats])
        if len(vec) < self.feature_dim:
            vec = np.pad(vec, (0, self.feature_dim - len(vec)))
        return vec[: self.feature_dim] / (np.linalg.norm(vec[: self.feature_dim]) + 1e-8)

    def _build_spatial_pyramid(self, pixels: np.ndarray) -> np.ndarray:
        pyramid = []
        gray = pixels.mean(axis=2) if pixels.ndim == 3 else pixels
        for level in [1, 2, 4]:
            h, w = gray.shape
            bh, bw = h // level, w // level
            if bh == 0 or bw == 0:
                continue
            blocks = []
            for i in range(level):
                for j in range(level):
                    block = gray[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]
                    blocks.append(block.mean())
            pyramid.extend(blocks)
        return np.array(pyramid, dtype=np.float64)

    def encode_text(self, text: str) -> np.ndarray:
        vec = np.zeros(self.feature_dim, dtype=np.float64)
        tokens = text.lower().split()
        for idx, token in enumerate(tokens):
            h = hash(token) % self.feature_dim
            vec[h] += 1.0
            vec[(h + 1) % self.feature_dim] += 0.5 * (idx + 1) / len(tokens)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def cross_modal_attention(self, image_features: np.ndarray, text_embedding: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        seq_len, dim = image_features.shape
        q = text_embedding.reshape(1, -1)
        k = image_features
        v = image_features
        scores = (q @ k.T) / np.sqrt(dim)
        attn_weights = self._softmax(scores)
        context = attn_weights @ v
        return context, attn_weights

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e / e.sum(axis=-1, keepdims=True)

    def answer_question(self, image_features: ImageFeatures, question: str) -> Dict[str, Any]:
        q_emb = self.encode_text(question)
        context, attn_weights = self.cross_modal_attention(image_features.features, q_emb)
        confidence = float(np.max(attn_weights))
        answer = self._synthesize_answer(context, question, image_features)
        return {
            "answer": answer,
            "confidence": confidence,
            "attention_weights": attn_weights.flatten().tolist(),
            "context_vector": context.flatten().tolist(),
        }

    def _synthesize_answer(self, context: np.ndarray, question: str, image_features: ImageFeatures) -> str:
        q_lower = question.lower()
        mean_color = image_features.pixels.mean(axis=(0, 1))
        dominant = int(mean_color.argmax())
        color_names = ["red", "green", "blue"]
        dominant_color = color_names[dominant] if dominant < len(color_names) else "mixed"
        region_count = len(image_features.regions)
        brightness = image_features.spatial_pyramid.mean() if image_features.spatial_pyramid is not None else 0.5

        if "color" in q_lower or "colour" in q_lower:
            return f"The dominant color is {dominant_color}."
        if "how many" in q_lower:
            return f"There are {region_count} distinct regions."
        if "where" in q_lower:
            return "The object is located in the center region of the image."
        if "what" in q_lower:
            return f"This appears to be a {dominant_color} scene with {region_count} visual elements."
        if "is" in q_lower and "there" in q_lower:
            return "Yes, the object is present in the image."
        if "bright" in q_lower or "dark" in q_lower:
            return "The image is bright." if brightness > 0.5 else "The image is dark."
        return f"Based on visual analysis, the scene contains {region_count} regions with dominant {dominant_color} tones."

    def generate_caption(self, image_features: ImageFeatures) -> str:
        mean_val = image_features.features.mean()
        num_regions = len(image_features.regions)
        brightness = "bright" if mean_val > 0 else "dark"
        captions = [
            f"A {brightness} scene with {num_regions} distinct regions.",
            f"An image containing {num_regions} visual elements in a {brightness} setting.",
            f"A {brightness} photograph with {num_regions} prominent areas.",
        ]
        return captions[int(abs(mean_val * 100)) % len(captions)]

    def compute_vqa_score(self, prediction: str, ground_truth: str) -> float:
        pred_tokens = set(prediction.lower().split())
        gt_tokens = set(ground_truth.lower().split())
        if not gt_tokens:
            return 0.0
        intersection = pred_tokens & gt_tokens
        precision = len(intersection) / len(pred_tokens) if pred_tokens else 0.0
        recall = len(intersection) / len(gt_tokens)
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)
