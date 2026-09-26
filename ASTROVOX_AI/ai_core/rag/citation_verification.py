"""Citation verification for RAG pipelines."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VerifiedCitation:
    citation_id: str
    chunk_id: str
    is_verified: bool
    confidence: float
    matched_passages: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class CitationVerifier:
    """Verify citations by matching claims against source document chunks."""

    def __init__(self, min_overlap: float = 0.25):
        self.min_overlap = min_overlap

    def verify(self, citation_id: str, chunk_id: str, claim: str, source_text: str) -> VerifiedCitation:
        matched = self._find_matches(claim, source_text)
        overlap = self._compute_overlap(claim, source_text)
        is_verified = overlap >= self.min_overlap
        return VerifiedCitation(
            citation_id=citation_id,
            chunk_id=chunk_id,
            is_verified=is_verified,
            confidence=overlap,
            matched_passages=matched,
        )

    def batch_verify(self, citations: List[Dict[str, str]], source_text: str) -> List[VerifiedCitation]:
        results = []
        for citation in citations:
            result = self.verify(
                citation_id=citation.get("citation_id", ""),
                chunk_id=citation.get("chunk_id", ""),
                claim=citation.get("claim", ""),
                source_text=source_text,
            )
            results.append(result)
        return results

    def _find_matches(self, claim: str, source_text: str) -> List[str]:
        claim_sentences = re.split(r"(?<=[.!?])\s+", claim)
        source_sentences = re.split(r"(?<=[.!?])\s+", source_text)
        matches = []
        for c_sent in claim_sentences:
            c_terms = set(c_sent.lower().split())
            for s_sent in source_sentences:
                s_terms = set(s_sent.lower().split())
                if len(c_terms & s_terms) / max(len(c_terms), 1) >= self.min_overlap:
                    matches.append(s_sent.strip())
        return matches

    def _compute_overlap(self, claim: str, source_text: str) -> float:
        claim_terms = set(claim.lower().split())
        source_terms = set(source_text.lower().split())
        if not claim_terms:
            return 0.0
        return len(claim_terms & source_terms) / len(claim_terms)
