"""Hallucination detection for RAG pipelines."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class HallucinationResult:
    chunk_id: str
    is_hallucination: bool
    confidence: float
    unsupported_claims: List[str]
    supporting_evidence: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class HallucinationDetector:
    """Detect hallucinations by verifying retrieved claims against source documents."""

    def __init__(self, similarity_threshold: float = 0.3):
        self.similarity_threshold = similarity_threshold

    def detect(self, query: str, retrieved_documents: List[Dict[str, Any]], generated_answer: str) -> HallucinationResult:
        claims = self._extract_claims(generated_answer)
        source_texts = [doc.get("content", "") for doc in retrieved_documents]
        combined_source = " ".join(source_texts)
        unsupported = []
        supported = []
        for claim in claims:
            if self._is_supported(claim, combined_source):
                supported.append(claim)
            else:
                unsupported.append(claim)
        total = len(claims) if claims else 1
        confidence = 1.0 - (len(unsupported) / total)
        return HallucinationResult(
            chunk_id=retrieved_documents[0].get("chunk_id", "") if retrieved_documents else "",
            is_hallucination=len(unsupported) > total / 2,
            confidence=confidence,
            unsupported_claims=unsupported,
            supporting_evidence=supported,
        )

    def batch_detect(self, query: str, document_sets: List[Tuple[List[Dict[str, Any]], str]]) -> List[HallucinationResult]:
        results = []
        for docs, answer in document_sets:
            results.append(self.detect(query, docs, answer))
        return results

    def _extract_claims(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        claims = [s.strip() for s in sentences if len(s.strip()) > 20]
        return claims

    def _is_supported(self, claim: str, source_text: str) -> bool:
        claim_terms = set(claim.lower().split())
        source_terms = set(source_text.lower().split())
        overlap = len(claim_terms & source_terms)
        return overlap / max(len(claim_terms), 1) >= self.similarity_threshold
