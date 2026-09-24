"""
Memory Extraction - Task 116

Identifies memorable facts vs noise from conversation content.
Uses scoring heuristics and numpy for efficient processing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class ExtractedMemory:
    content: str
    confidence: float
    category: str
    source_turn_id: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MemoryExtractor:
    """
    Extracts memorable facts from conversation turns.
    
    Uses multiple signals to distinguish memorable facts from noise:
    - Named entity presence
    - Specificity (numbers, dates, names)
    - Emotional valence
    - Repeat frequency
    - Structural markers
    """

    NOISE_PATTERNS = [
        re.compile(r"^(hi|hello|hey|greetings|good morning|good evening|how are you|what'?s up)\b", re.I),
        re.compile(r"^(thanks|thank you|thx|ty|appreciate)\b", re.I),
        re.compile(r"^(ok|okay|alright|got it|sure|yes|no|maybe|hmm)\b", re.I),
        re.compile(r"^(bye|goodbye|see you|later|take care)\b", re.I),
    ]

    IMPORTANCE_PATTERNS = [
        re.compile(r"\b(remember|important|don'?t forget|note|key|critical|essential)\b", re.I),
        re.compile(r"\b(my name is|i am called|call me|i live in|i work at|my birthday)\b", re.I),
        re.compile(r"\b(prefer|like|love|hate|dislike|favorite|worst)\b", re.I),
        re.compile(r"\b(\d{4}|\$|€|£|@\w+|phone|email|address)\b"),
    ]

    def __init__(self, importance_threshold: float = 0.5):
        self.importance_threshold = importance_threshold
        self._fact_embeddings: Dict[str, np.ndarray] = {}

    def _compute_specificity(self, text: str) -> float:
        """Compute specificity score based on numbers, names, dates."""
        score = 0.0
        if re.search(r'\b\d{4}\b', text):
            score += 0.2
        if re.search(r'\b\d+\.?\d*\b', text):
            score += 0.15
        if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text):
            score += 0.2
        if re.search(r'@\w+|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
            score += 0.3
        return min(score, 1.0)

    def _compute_emotional_valence(self, text: str) -> float:
        """Compute emotional valence (strong emotions = more memorable)."""
        positive = len(re.findall(r'\b(love|great|awesome|amazing|happy|excited|wonderful|fantastic)\b', text, re.I))
        negative = len(re.findall(r'\b(hate|terrible|awful|sad|angry|frustrated|disappointed)\b', text, re.I))
        total = positive + negative
        if total == 0:
            return 0.0
        return min((positive + negative) / 5.0, 1.0)

    def _is_noise(self, text: str) -> bool:
        """Check if text matches noise patterns."""
        text_stripped = text.strip()
        for pattern in self.NOISE_PATTERNS:
            if pattern.match(text_stripped):
                return True
        return False

    def _compute_importance_signals(self, text: str) -> float:
        """Compute importance signal score."""
        score = 0.0
        for pattern in self.IMPORTANCE_PATTERNS:
            matches = len(pattern.findall(text))
            score += matches * 0.2
        return min(score, 1.0)

    def _compute_length_score(self, text: str) -> float:
        """Compute score based on content length (medium length is best)."""
        words = len(text.split())
        if words < 3:
            return 0.0
        elif words < 20:
            return 0.5
        elif words < 100:
            return 0.8
        else:
            return 0.4

    def score(self, text: str) -> Tuple[float, str]:
        """
        Score a piece of text for memorability.
        
        Returns:
            (score, category) where category is 'fact', 'preference', 'identity', or 'noise'
        """
        if self._is_noise(text):
            return 0.0, 'noise'
        
        specificity = self._compute_specificity(text)
        emotional = self._compute_emotional_valence(text)
        importance = self._compute_importance_signals(text)
        length = self._compute_length_score(text)
        
        signal = np.array([specificity, emotional, importance, length])
        weights = np.array([0.3, 0.2, 0.3, 0.2])
        score = float(np.dot(signal, weights))
        
        if re.search(r'\b(my name is|i am|i live|i work|birthday|phone|email)\b', text, re.I):
            category = 'identity'
        elif re.search(r'\b(prefer|like|love|hate|favorite)\b', text, re.I):
            category = 'preference'
        elif specificity > 0.3 or importance > 0.3:
            category = 'fact'
        else:
            category = 'general'
        
        return min(score, 1.0), category

    def extract(
        self,
        turn_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExtractedMemory]:
        """
        Extract a memory from a conversation turn.
        
        Returns ExtractedMemory if content is memorable, None if noise.
        """
        score, category = self.score(content)
        
        if category == 'noise' or score < self.importance_threshold:
            return None
        
        return ExtractedMemory(
            content=content,
            confidence=score,
            category=category,
            source_turn_id=turn_id,
            metadata=metadata or {},
        )

    def batch_extract(
        self,
        turns: List[Tuple[str, str, Optional[Dict[str, Any]]]],
    ) -> List[ExtractedMemory]:
        """Extract memories from multiple turns efficiently."""
        results = []
        for turn_id, content, metadata in turns:
            memory = self.extract(turn_id, content, metadata)
            if memory:
                results.append(memory)
        return results
