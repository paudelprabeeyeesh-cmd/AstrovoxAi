import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VideoTranscriptionConfig:
    model_name: str = "whisper"
    language: str = "en"
    device: str = "cpu"


class VideoTranscriber:
    def __init__(self, config: Optional[VideoTranscriptionConfig] = None):
        self.config = config or VideoTranscriptionConfig()
        logger.info("Video transcriber initialized with model %s", self.config.model_name)

    def transcribe(self, video_path: str) -> dict:
        logger.info("Transcribing %s", video_path)
        return {"text": "", "segments": []}

    def transcribe_batch(self, video_paths: List[str]) -> List[dict]:
        return [self.transcribe(path) for path in video_paths]
