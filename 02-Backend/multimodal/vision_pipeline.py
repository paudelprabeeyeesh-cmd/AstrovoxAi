import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from multimodal.vision_language import ImageFeatures, VisionLanguageModel


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
        self.model = VisionLanguageModel(feature_dim=feature_dim, num_regions=num_regions)

    def process(self, pixels: np.ndarray) -> VisionPipelineResult:
        feats = self.model.encode_image(pixels)
        caption = self.model.generate_caption(feats)
        vqa_score = self.model.compute_vqa_score(caption, caption)
        return VisionPipelineResult(
            features=feats,
            caption=caption,
            vqa_score=vqa_score,
            metadata={
                "num_regions": len(feats.regions),
                "shape": pixels.shape,
            },
        )
