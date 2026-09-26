import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ImageCaptionConfig:
    model_name: str = "caption-model"
    max_length: int = 50


class ImageCaptioner:
    def __init__(self, config: Optional[ImageCaptionConfig] = None):
        self.config = config or ImageCaptionConfig()
        logger.info("Image captioner initialized")

    def caption(self, image_path: str) -> str:
        logger.info("Generating caption for %s", image_path)
        return ""

    def caption_batch(self, image_paths: List[str]) -> List[str]:
        return [self.caption(path) for path in image_paths]
