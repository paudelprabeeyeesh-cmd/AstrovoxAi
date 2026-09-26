import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetadataEnrichmentConfig:
    enable_language: bool = True
    enable_quality: bool = True
    enable_pii_scan: bool = True
    enable_topic: bool = True


class MetadataEnricher:
    def __init__(self, config: Optional[MetadataEnrichmentConfig] = None):
        self.config = config or MetadataEnrichmentConfig()
        logger.info("Metadata enricher initialized")

    def enrich(self, document: Dict[str, Any]) -> Dict[str, Any]:
        text = document.get("content", "") or document.get("text", "")
        metadata = dict(document.get("metadata", {}))

        if self.config.enable_language:
            try:
                from .language_detection import LanguageDetector
                detector = LanguageDetector()
                lang, confidence = detector.detect_with_confidence(text)
                metadata["language"] = lang
                metadata["language_confidence"] = confidence
            except Exception as exc:
                logger.warning("Language detection failed: %s", exc)

        if self.config.enable_quality:
            try:
                from .quality_scoring import QualityScorer
                scorer = QualityScorer()
                metadata["quality_score"] = scorer.score(text)
            except Exception as exc:
                logger.warning("Quality scoring failed: %s", exc)

        if self.config.enable_pii_scan:
            try:
                from .pii_removal import PiiRemover
                remover = PiiRemover()
                pii = remover.find_pii(text)
                metadata["pii_categories"] = list(pii.keys())
                metadata["pii_count"] = sum(len(v) for v in pii.values())
            except Exception as exc:
                logger.warning("PII scan failed: %s", exc)

        if self.config.enable_topic:
            words = text.split()
            metadata["word_count"] = len(words)
            metadata["char_count"] = len(text)

        enriched = dict(document)
        enriched["metadata"] = metadata
        return enriched

    def enrich_batch(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.enrich(doc) for doc in documents]
