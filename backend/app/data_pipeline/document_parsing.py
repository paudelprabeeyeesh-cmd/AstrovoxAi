import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentParsingConfig:
    supported_formats: List[str] = None

    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ["pdf", "docx", "txt", "html", "md"]


class DocumentParser:
    def __init__(self, config: Optional[DocumentParsingConfig] = None):
        self.config = config or DocumentParsingConfig()
        logger.info("Document parser initialized for formats: %s", self.config.supported_formats)

    def parse(self, file_path: str, content_type: str) -> str:
        logger.info("Parsing %s as %s", file_path, content_type)
        return ""

    def parse_batch(self, files: List[dict]) -> List[str]:
        return [self.parse(f["path"], f["type"]) for f in files]
