"""Summarizer agent for content summarization."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Summary:
    original_text: str
    summary_text: str
    compression_ratio: float
    word_count_original: int
    word_count_summary: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SummarizerAgent:
    _summaries: Dict[str, Summary] = {}

    @classmethod
    def summarize(cls, text: str, max_length: int = 200) -> Summary:
        words = text.split()
        word_count_original = len(words)
        if word_count_original <= max_length:
            summary_text = text
            compression_ratio = 1.0
        else:
            summary_words = words[:max_length]
            summary_text = " ".join(summary_words) + "..."
            compression_ratio = len(summary_words) / word_count_original
        summary = Summary(
            original_text=text,
            summary_text=summary_text,
            compression_ratio=compression_ratio,
            word_count_original=word_count_original,
            word_count_summary=len(summary_text.split()),
        )
        cls._summaries[hash(text)] = summary
        return summary
