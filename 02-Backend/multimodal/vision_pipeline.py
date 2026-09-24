from dataclasses import dataclass, field
from math import sqrt
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ImageFeatures:
    pixels: List[List[List[int]]]
    features: List[List[float]]
    regions: List[Tuple[int, int, int, int]]
    spatial_pyramid: Optional[List[float]] = None


@dataclass
class VisionPipelineResult:
    features: ImageFeatures
    caption: str
    vqa_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class VisionPipeline:
    def __init__(self, feature_dim: int = 256, num_regions: int = 9):
        self.feature_dim = feature_dim
        self.num_regions = num_regions

    def _to_list(self, obj):
        if hasattr(obj, "tolist"):
            return obj.tolist()
        if isinstance(obj, list):
            return obj
        return list(obj)

    def _ensure_rgb(self, pixels: List[List[List[int]]]) -> List[List[List[int]]]:
        if not pixels or not pixels[0] or not pixels[0][0]:
            return pixels
        if len(pixels[0][0]) == 1:
            return [[[p[0], p[0], p[0]] for p in row] for row in pixels]
        return pixels

    def _propose_regions(self, h: int, w: int) -> List[Tuple[int, int, int, int]]:
        grid = _ceil(sqrt(self.num_regions))
        rh, rw = max(1, h // grid), max(1, w // grid)
        regions = []
        for i in range(grid):
            for j in range(grid):
                y1, x1 = i * rh, j * rw
                y2, x2 = min((i + 1) * rh, h), min((j + 1) * rw, w)
                regions.append((y1, x1, y2, x2))
        return regions[: self.num_regions]

    def _patch_to_vector(self, patch: List[List[List[int]]]) -> List[float]:
        hist_r = [0.0] * 16
        hist_g = [0.0] * 16
        hist_b = [0.0] * 16
        count = 0
        for row in patch:
            for p in row:
                hist_r[min(p[0] // 16, 15)] += 1
                hist_g[min(p[1] // 16, 15)] += 1
                hist_b[min(p[2] // 16, 15)] += 1
                count += 1
        if count > 0:
            hist_r = [x / count for x in hist_r]
            hist_g = [x / count for x in hist_g]
            hist_b = [x / count for x in hist_b]
        s = sum(sum(p[0] for p in row) for row in patch)
        mean_val = s / (count * 3) if count else 0.0
        all_r = [p[0] for row in patch for p in row]
        min_val = min(all_r) if all_r else 0
        max_val = max(all_r) if all_r else 0
        vec = hist_r + hist_g + hist_b + [mean_val, 0.0, float(min_val), float(max_val)]
        norm = sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec[: self.feature_dim]

    def _build_spatial_pyramid(self, pixels: List[List[List[int]]]) -> List[float]:
        h = len(pixels)
        w = len(pixels[0]) if h > 0 else 0
        pyramid = []
        for level in [1, 2, 4]:
            bh, bw = h // level, w // level
            if bh == 0 or bw == 0:
                continue
            for i in range(level):
                for j in range(level):
                    s = 0.0
                    cnt = 0
                    for bi in range(i * bh, min((i + 1) * bh, h)):
                        for bj in range(j * bw, min((j + 1) * bw, w)):
                            s += sum(pixels[bi][bj]) / 3
                            cnt += 1
                    pyramid.append(s / cnt if cnt else 0.0)
        return pyramid

    def encode_image(self, pixels) -> ImageFeatures:
        pixels = self._to_list(pixels)
        h = len(pixels)
        w = len(pixels[0]) if h > 0 else 0
        pixels = self._ensure_rgb(pixels)
        regions = self._propose_regions(h, w)
        features = []
        for (y1, x1, y2, x2) in regions:
            patch = [row[x1:x2] for row in pixels[y1:y2]]
            if not patch or not patch[0]:
                features.append([0.0] * self.feature_dim)
            else:
                features.append(self._patch_to_vector(patch))
        spatial_pyramid = self._build_spatial_pyramid(pixels)
        return ImageFeatures(
            pixels=pixels,
            features=features,
            regions=regions,
            spatial_pyramid=spatial_pyramid,
        )

    def generate_caption(self, features: ImageFeatures) -> str:
        mean_val = sum(f[0] for f in features.features) / len(features.features) if features.features else 0
        num_regions = len(features.regions)
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

    def process(self, pixels) -> VisionPipelineResult:
        pixels = self._to_list(pixels)
        feats = self.encode_image(pixels)
        caption = self.generate_caption(feats)
        vqa_score = self.compute_vqa_score(caption, caption)
        return VisionPipelineResult(
            features=feats,
            caption=caption,
            vqa_score=vqa_score,
            metadata={
                "num_regions": len(feats.regions),
                "shape": (len(pixels), len(pixels[0]) if pixels else 0, len(pixels[0][0]) if pixels and pixels[0] else 0),
            },
        )


def _ceil(x: float) -> int:
    return int(x) + (1 if x != int(x) else 0)
